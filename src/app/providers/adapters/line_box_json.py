"""line_box_json adapter — handles providers that return lines with bboxes but no word segmentation.

Expected payload format:
    [
        {"text": "line text", "bbox": [x1, y1, x2, y2], "confidence": 0.95},
        ...
    ]
    or:
    [
        {"text": "line text", "bbox": [x, y, w, h], "confidence": 0.95, "format": "xywh"},
        ...
    ]

Each item is treated as a text line. A single word per line is created
since the provider doesn't segment words. The block is inferred.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.domain.models import (
    CanonicalDocument,
    Geometry,
    Provenance,
    RawProviderPayload,
)
from src.app.domain.models.status import EvidenceType, GeometryStatus, InputType
from src.app.geometry.bbox import union_all
from src.app.geometry.normalization import xyxy_to_xywh
from src.app.normalization.canonical_builder import CanonicalBuilder
from src.app.providers.adapters.base import BaseAdapter

if TYPE_CHECKING:
    from src.app.domain.models.geometry import GeometryContext


class LineBoxJsonAdapter(BaseAdapter):
    """Adapter for the line_box_json family."""

    @property
    def family(self) -> str:
        return "line_box_json"

    @property
    def version(self) -> str:
        return "adapter.line_box_json.v1"

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
                f"line_box_json expects a list payload, got {type(payload).__name__}"
            )
        if not payload:
            raise ValueError("line_box_json payload contains no items")

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

        line_bboxes: list[tuple[float, float, float, float]] = []
        line_data: list[dict] = []

        for idx, item in enumerate(payload):
            if not isinstance(item, dict):
                raise ValueError(f"Item {idx}: expected dict, got {type(item).__name__}")

            text = str(item.get("text", ""))
            if not text:
                continue

            raw_bbox = item.get("bbox")
            if not raw_bbox or len(raw_bbox) != 4:
                raise ValueError(f"Item {idx}: missing or invalid bbox")

            # Determine format: default is xyxy, "xywh" if specified
            fmt = item.get("format", "xyxy")
            if fmt == "xywh":
                bbox = (float(raw_bbox[0]), float(raw_bbox[1]),
                        float(raw_bbox[2]), float(raw_bbox[3]))
            else:
                bbox = xyxy_to_xywh(tuple(float(v) for v in raw_bbox))

            confidence = item.get("confidence")
            if confidence is not None:
                confidence = max(0.0, min(1.0, float(confidence)))

            line_bboxes.append(bbox)
            line_data.append({
                "bbox": bbox,
                "text": text,
                "confidence": confidence,
                "source_idx": idx,
            })

        if not line_data:
            raise ValueError("line_box_json payload contains no valid items")

        block_bbox = union_all(line_bboxes)
        block_prov = Provenance(
            provider=raw.provider_id,
            adapter=self.version,
            source_ref="$",
            evidence_type=EvidenceType.DERIVED,
            derived_from=[f"tl{i+1}" for i in range(len(line_data))],
        )

        region = page.add_text_region(
            region_id="tb1",
            geometry=Geometry(bbox=block_bbox, status=GeometryStatus.INFERRED),
            provenance=block_prov,
        )

        for i, ld in enumerate(line_data):
            line_id = f"tl{i + 1}"
            word_id = f"w{i + 1}"

            prov = Provenance(
                provider=raw.provider_id,
                adapter=self.version,
                source_ref=f"$[{ld['source_idx']}]",
                evidence_type=EvidenceType.PROVIDER_NATIVE,
            )

            geo = Geometry(bbox=ld["bbox"], status=GeometryStatus.EXACT)

            line = region.add_line(line_id, geometry=geo, provenance=prov)
            line.add_word(
                word_id,
                text=ld["text"],
                geometry=geo,
                provenance=prov,
                confidence=ld["confidence"],
            )

        return builder.build()
