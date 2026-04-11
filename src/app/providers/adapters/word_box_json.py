"""word_box_json adapter — handles PaddleOCR and similar providers.

PaddleOCR output format (standard):
    [
        [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ("text", confidence)],
        ...
    ]

Each item is a detected text line/word with a 4-point polygon and
a (text, confidence) tuple.  This adapter treats each item as a word
within a single inferred text block.
"""

from __future__ import annotations

from src.app.domain.models import (
    CanonicalDocument,
    Geometry,
    Provenance,
    RawProviderPayload,
)
from src.app.domain.models.geometry import GeometryContext
from src.app.domain.models.status import (
    EvidenceType,
    GeometryStatus,
    InputType,
)
from src.app.geometry.bbox import union_all
from src.app.geometry.normalization import four_point_to_polygon, four_point_to_xywh
from src.app.normalization.canonical_builder import CanonicalBuilder
from src.app.providers.adapters.base import BaseAdapter


class WordBoxJsonAdapter(BaseAdapter):
    """Adapter for the word_box_json family (PaddleOCR, etc.)."""

    @property
    def family(self) -> str:
        return "word_box_json"

    @property
    def version(self) -> str:
        return "adapter.word_box_json.v1"

    def normalize(
        self,
        raw: RawProviderPayload,
        geometry_context: GeometryContext,
        *,
        document_id: str,
        source_filename: str | None = None,
    ) -> CanonicalDocument:
        payload = raw.payload
        if not isinstance(payload, list):
            raise ValueError(
                f"word_box_json expects a list payload, got {type(payload).__name__}"
            )

        builder = CanonicalBuilder(
            document_id=document_id,
            input_type=InputType.IMAGE,
            filename=source_filename,
        )

        page = builder.add_page(
            page_id="p1",
            page_index=0,
            width=geometry_context.source_width,
            height=geometry_context.source_height,
        )

        # Collect all word bboxes for building a block-level bbox
        word_bboxes: list[tuple[float, float, float, float]] = []
        word_data: list[dict] = []

        for idx, item in enumerate(payload):
            points, text_conf = self._parse_item(item, idx)
            text, confidence = self._parse_text_conf(text_conf, idx)

            bbox = four_point_to_xywh(points)
            polygon = four_point_to_polygon(points)

            # Apply resize factor if present
            if geometry_context.resize_factor and geometry_context.resize_factor != 1.0:
                factor = 1.0 / geometry_context.resize_factor
                bbox = (bbox[0] * factor, bbox[1] * factor, bbox[2] * factor, bbox[3] * factor)
                polygon = [(x * factor, y * factor) for x, y in polygon]

            word_bboxes.append(bbox)
            word_data.append({
                "bbox": bbox,
                "polygon": polygon,
                "text": text,
                "confidence": confidence,
                "source_idx": idx,
            })

        if not word_data:
            raise ValueError("word_box_json payload contains no items")

        # Build a single inferred text block containing all items as words
        # Each PaddleOCR item is treated as a line with one word
        block_bbox = union_all(word_bboxes)
        block_prov = Provenance(
            provider=raw.provider_id,
            adapter=self.version,
            source_ref="$",
            evidence_type=EvidenceType.DERIVED,
            derived_from=[f"w{i+1}" for i in range(len(word_data))],
        )

        region = page.add_text_region(
            region_id="tb1",
            geometry=Geometry(
                bbox=block_bbox,
                status=GeometryStatus.INFERRED,
            ),
            provenance=block_prov,
        )

        for i, wd in enumerate(word_data):
            word_id = f"w{i + 1}"
            line_id = f"tl{i + 1}"

            prov = Provenance(
                provider=raw.provider_id,
                adapter=self.version,
                source_ref=f"$[{wd['source_idx']}]",
                evidence_type=EvidenceType.PROVIDER_NATIVE,
            )

            geo = Geometry(
                bbox=wd["bbox"],
                polygon=wd["polygon"],
                status=GeometryStatus.EXACT,
            )

            # Each PaddleOCR detection becomes a line with one word
            line = region.add_line(line_id, geometry=geo, provenance=prov)
            line.add_word(
                word_id,
                text=wd["text"],
                geometry=geo,
                provenance=prov,
                confidence=wd["confidence"],
            )

        return builder.build()

    # -- Private helpers ---------------------------------------------------------

    @staticmethod
    def _parse_item(item: object, idx: int) -> tuple[list, object]:
        """Extract (points, text_conf) from a PaddleOCR result item."""
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(
                f"Item {idx}: expected [points, (text, conf)], got {type(item).__name__}"
            )
        points = item[0]
        text_conf = item[1]
        if not isinstance(points, list) or len(points) != 4:
            raise ValueError(
                f"Item {idx}: expected 4 polygon points, got {len(points) if isinstance(points, list) else type(points).__name__}"
            )
        return points, text_conf

    @staticmethod
    def _parse_text_conf(text_conf: object, idx: int) -> tuple[str, float | None]:
        """Extract (text, confidence) from the second element."""
        if isinstance(text_conf, (list, tuple)) and len(text_conf) == 2:
            text = str(text_conf[0])
            try:
                confidence = float(text_conf[1])
                confidence = max(0.0, min(1.0, confidence))
            except (TypeError, ValueError):
                confidence = None
            return text, confidence
        if isinstance(text_conf, str):
            return text_conf, None
        raise ValueError(
            f"Item {idx}: expected (text, confidence) or text string, "
            f"got {type(text_conf).__name__}"
        )
