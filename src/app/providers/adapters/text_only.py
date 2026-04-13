"""text_only adapter — handles providers that return structured text without geometry.

Expected payload format:
    {
        "text": "full page text",
        "blocks": [                     # optional
            {"text": "block text"},
            ...
        ]
    }
    or simply:
    {"text": "full text"}

This adapter is honest: geometry is marked as 'unknown' since the
provider doesn't supply coordinates. ALTO export will be refused
(no word geometry), but PAGE export may be partial and the viewer
will show text without positioned overlays.
"""

from __future__ import annotations

from src.app.domain.models import (
    CanonicalDocument,
    Geometry,
    Provenance,
    RawProviderPayload,
)
from src.app.domain.models.geometry import GeometryContext
from src.app.domain.models.status import EvidenceType, GeometryStatus, InputType
from src.app.normalization.canonical_builder import CanonicalBuilder
from src.app.providers.adapters.base import BaseAdapter


class TextOnlyAdapter(BaseAdapter):
    """Adapter for the text_only family (mLLM without geometry)."""

    @property
    def family(self) -> str:
        return "text_only"

    @property
    def version(self) -> str:
        return "adapter.text_only.v1"

    def normalize(
        self,
        raw: RawProviderPayload,
        geometry_context: GeometryContext,
        *,
        document_id: str,
        source_filename: str | None = None,
    ) -> CanonicalDocument:
        payload = raw.payload
        if not isinstance(payload, dict):
            raise ValueError(
                f"text_only expects a dict payload, got {type(payload).__name__}"
            )

        builder = CanonicalBuilder(
            document_id=document_id,
            input_type=InputType.IMAGE,
            filename=source_filename,
        )

        page_w = geometry_context.source_width
        page_h = geometry_context.source_height

        page = builder.add_page("p1", 0, page_w, page_h)

        # Placeholder bbox covering the full page — marked unknown
        full_page_geo = Geometry(
            bbox=(0, 0, page_w, page_h),
            status=GeometryStatus.UNKNOWN,
        )

        # Extract text blocks
        blocks = payload.get("blocks")
        if blocks and isinstance(blocks, list):
            texts = [str(b.get("text", "")) for b in blocks if isinstance(b, dict) and b.get("text")]
        else:
            # Single text blob — split into paragraphs
            full_text = str(payload.get("text", ""))
            if not full_text.strip():
                raise ValueError("text_only payload has no text content")
            texts = [p.strip() for p in full_text.split("\n\n") if p.strip()]
            if not texts:
                texts = [full_text.strip()]

        for bi, block_text in enumerate(texts):
            block_id = f"tb{bi + 1}"
            prov = Provenance(
                provider=raw.provider_id,
                adapter=self.version,
                source_ref=f"$.blocks[{bi}]" if blocks else f"$.text.paragraph[{bi}]",
                evidence_type=EvidenceType.PROVIDER_NATIVE,
            )

            region = page.add_text_region(
                region_id=block_id,
                geometry=full_page_geo,
                provenance=prov,
            )

            # Split block into lines
            lines = [l.strip() for l in block_text.split("\n") if l.strip()]
            if not lines:
                lines = [block_text]

            for li, line_text in enumerate(lines):
                line_id = f"tl{bi + 1}_{li + 1}"
                word_id = f"w{bi + 1}_{li + 1}"

                line = region.add_line(
                    line_id, geometry=full_page_geo, provenance=prov,
                )
                # Each line becomes a single word (no word segmentation available)
                line.add_word(
                    word_id,
                    text=line_text,
                    geometry=full_page_geo,
                    provenance=prov,
                )

        return builder.build()
