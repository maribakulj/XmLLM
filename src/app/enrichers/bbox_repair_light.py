"""bbox_repair_light enricher — clips bboxes that overflow the page.

Light repair only:
  - Clips bboxes to page boundaries
  - Marks repaired geometry as 'repaired'
  - Does NOT reconstruct or invent geometry
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.domain.models.status import GeometryStatus
from src.app.enrichers import BaseEnricher
from src.app.geometry.bbox import contains
from src.app.geometry.transforms import clip_bbox_to_page

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument
    from src.app.policies.document_policy import DocumentPolicy


class BboxRepairLightEnricher(BaseEnricher):
    @property
    def name(self) -> str:
        return "bbox_repair_light"

    def enrich(
        self, doc: CanonicalDocument, policy: DocumentPolicy
    ) -> CanonicalDocument:
        new_pages = []
        changed = False

        for page in doc.pages:
            page_w, page_h = page.width, page.height
            page_bbox = (0.0, 0.0, page_w, page_h)
            new_regions = []

            for region in page.text_regions:
                region_out = self._clip_node(region, page_w, page_h, page_bbox)
                new_lines = []
                for line in region_out.lines:
                    line_out = self._clip_node(line, page_w, page_h, page_bbox)
                    new_words = []
                    for word in line_out.words:
                        new_words.append(self._clip_node(word, page_w, page_h, page_bbox))
                    line_out = line_out.model_copy(update={"words": new_words})
                    new_lines.append(line_out)
                region_out = region_out.model_copy(update={"lines": new_lines})
                new_regions.append(region_out)

            new_page = page.model_copy(update={"text_regions": new_regions})
            new_pages.append(new_page)
            if new_page != page:
                changed = True

        if changed:
            return doc.model_copy(update={"pages": new_pages})
        return doc

    @staticmethod
    def _clip_node(node: object, page_w: float, page_h: float, page_bbox: tuple) -> object:
        """Clip a node's bbox to page boundaries if it overflows."""
        geo = getattr(node, "geometry", None)
        if geo is None:
            return node

        if contains(page_bbox, geo.bbox, tolerance=0):
            return node

        clipped = clip_bbox_to_page(geo.bbox, page_w, page_h)
        if clipped == geo.bbox:
            return node

        new_geo = geo.model_copy(update={
            "bbox": clipped,
            "status": GeometryStatus.REPAIRED,
        })
        return node.model_copy(update={"geometry": new_geo})  # type: ignore[union-attr]
