"""reading_order_simple enricher — infers reading order from spatial position.

If a page has no reading order, orders text regions top-to-bottom,
left-to-right using the center of each region's bbox.
"""

from __future__ import annotations

from src.app.domain.models import CanonicalDocument
from src.app.enrichers import BaseEnricher
from src.app.geometry.bbox import center
from src.app.policies.document_policy import DocumentPolicy


class ReadingOrderSimpleEnricher(BaseEnricher):
    @property
    def name(self) -> str:
        return "reading_order_simple"

    def enrich(
        self, doc: CanonicalDocument, policy: DocumentPolicy
    ) -> CanonicalDocument:
        if not policy.allow_reading_order_inference:
            return doc

        new_pages = []
        changed = False

        for page in doc.pages:
            if page.reading_order or not page.text_regions:
                new_pages.append(page)
                continue

            # Sort regions by center-y then center-x (top-to-bottom, left-to-right)
            sorted_regions = sorted(
                page.text_regions,
                key=lambda r: (center(r.geometry.bbox)[1], center(r.geometry.bbox)[0]),
            )
            new_order = [r.id for r in sorted_regions]
            new_pages.append(page.model_copy(update={"reading_order": new_order}))
            changed = True

        if changed:
            return doc.model_copy(update={"pages": new_pages})
        return doc
