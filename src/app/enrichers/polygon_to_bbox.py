"""polygon_to_bbox enricher — derives bbox from polygon when bbox is missing/unknown.

If a node has a polygon but its geometry status is 'unknown', computes the
axis-aligned bounding box and marks the geometry as 'inferred'.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.domain.models.status import GeometryStatus
from src.app.enrichers import BaseEnricher
from src.app.geometry.polygon import polygon_to_bbox as _poly_to_bbox

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument
    from src.app.policies.document_policy import DocumentPolicy


class PolygonToBboxEnricher(BaseEnricher):
    @property
    def name(self) -> str:
        return "polygon_to_bbox"

    def enrich(
        self, doc: CanonicalDocument, policy: DocumentPolicy
    ) -> CanonicalDocument:
        if not policy.allow_polygon_to_bbox:
            return doc

        new_pages = []
        for page in doc.pages:
            new_regions = []
            for region in page.text_regions:
                new_lines = []
                for line in region.lines:
                    new_words = [self._maybe_fix(w) for w in line.words]
                    new_lines.append(
                        line.model_copy(update={"words": new_words})
                        if new_words != list(line.words)
                        else line
                    )
                    new_lines[-1] = self._maybe_fix_node(new_lines[-1])
                new_regions.append(
                    region.model_copy(update={"lines": new_lines})
                    if new_lines != list(region.lines)
                    else region
                )
                new_regions[-1] = self._maybe_fix_node(new_regions[-1])
            new_pages.append(
                page.model_copy(update={"text_regions": new_regions})
                if new_regions != list(page.text_regions)
                else page
            )

        if new_pages != list(doc.pages):
            return doc.model_copy(update={"pages": new_pages})
        return doc

    def _maybe_fix(self, word: object) -> object:
        """Fix a word if it has polygon but unknown bbox."""
        return self._maybe_fix_node(word)

    @staticmethod
    def _maybe_fix_node(node: object) -> object:
        """Generic: if node.geometry has polygon and status is unknown, derive bbox."""
        geo = getattr(node, "geometry", None)
        if geo is None:
            return node
        if geo.status != GeometryStatus.UNKNOWN:
            return node
        if not geo.polygon or len(geo.polygon) < 3:
            return node

        new_bbox = _poly_to_bbox(geo.polygon)
        new_geo = geo.model_copy(update={
            "bbox": new_bbox,
            "status": GeometryStatus.INFERRED,
        })
        return node.model_copy(update={"geometry": new_geo})  # type: ignore[union-attr]
