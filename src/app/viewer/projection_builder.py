"""ViewerProjection builder — converts CanonicalDocument into viewer data.

The ViewerProjection is a lightweight structure that the front-end
consumes directly. It never parses XML. It derives from the canonical
document after validation and enrichment.
"""

from __future__ import annotations

from src.app.domain.models import CanonicalDocument, Page
from src.app.domain.models.readiness import ExportEligibility
from src.app.domain.models.viewer_projection import InspectionData, OverlayItem, ViewerProjection
from src.app.viewer.overlays import (
    line_to_inspection,
    line_to_overlay,
    non_text_to_overlay,
    region_to_inspection,
    region_to_overlay,
    word_to_inspection,
    word_to_overlay,
)


def build_projection(
    doc: CanonicalDocument,
    page_index: int = 0,
    *,
    export_status: ExportEligibility | None = None,
) -> ViewerProjection:
    """Build a ViewerProjection for a single page.

    Args:
        doc: The canonical document.
        page_index: Which page to project (default: first).
        export_status: Export eligibility to include in the projection.

    Returns:
        A ViewerProjection ready for the front-end.
    """
    if page_index >= len(doc.pages):
        raise ValueError(f"Page index {page_index} out of range (document has {len(doc.pages)} pages)")

    page = doc.pages[page_index]

    block_overlays: list[OverlayItem] = []
    line_overlays: list[OverlayItem] = []
    word_overlays: list[OverlayItem] = []
    non_text_overlays: list[OverlayItem] = []
    inspection_index: dict[str, InspectionData] = {}
    validation_flags: list[str] = list(page.warnings)

    for region in page.text_regions:
        block_overlays.append(region_to_overlay(region))
        inspection_index[region.id] = region_to_inspection(region)

        for line in region.lines:
            line_overlays.append(line_to_overlay(line))
            inspection_index[line.id] = line_to_inspection(line)

            for word in line.words:
                word_overlays.append(word_to_overlay(word))
                inspection_index[word.id] = word_to_inspection(word)

    for ntr in page.non_text_regions:
        non_text_overlays.append(non_text_to_overlay(ntr))

    image_ref = ""
    if doc.source.filename:
        image_ref = doc.source.filename
    if page.metadata and "image_ref" in page.metadata:
        image_ref = page.metadata["image_ref"]

    return ViewerProjection(
        image_ref=image_ref,
        image_width=int(page.width),
        image_height=int(page.height),
        block_overlays=block_overlays,
        line_overlays=line_overlays,
        word_overlays=word_overlays,
        non_text_overlays=non_text_overlays,
        inspection_index=inspection_index,
        validation_flags=validation_flags,
        export_status=export_status or ExportEligibility(),
    )


def build_all_projections(
    doc: CanonicalDocument,
    *,
    export_status: ExportEligibility | None = None,
) -> list[ViewerProjection]:
    """Build ViewerProjections for all pages."""
    return [
        build_projection(doc, i, export_status=export_status)
        for i in range(len(doc.pages))
    ]
