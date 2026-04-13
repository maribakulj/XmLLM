"""Readiness validator — computes how ready a document is for export.

Produces AltoReadiness / PageXmlReadiness per page and DocumentReadiness
at document level.  Does NOT decide whether to allow export — that's the
export eligibility validator's job.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.domain.models.readiness import (
    AltoReadiness,
    DocumentReadiness,
    PageXmlReadiness,
)
from src.app.domain.models.status import (
    GeometryStatus,
    MissingCapability,
    ReadinessLevel,
)

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument, Page


def compute_page_alto_readiness(page: Page) -> AltoReadiness:
    """Compute ALTO readiness for a single page.

    ALTO full requires: page dimensions, block bbox, line bbox, word bbox, word text.
    """
    missing: list[MissingCapability] = []

    if page.width <= 0 or page.height <= 0:
        missing.append(MissingCapability.PAGE_DIMENSIONS)

    has_blocks = len(page.text_regions) > 0
    has_lines = False
    has_words = False
    has_word_geo = True
    has_word_text = True
    has_confidence = True

    for region in page.text_regions:
        if (
            region.geometry.status == GeometryStatus.UNKNOWN
            and MissingCapability.BLOCK_GEOMETRY not in missing
        ):
            missing.append(MissingCapability.BLOCK_GEOMETRY)
        for line in region.lines:
            has_lines = True
            if (
                line.geometry.status == GeometryStatus.UNKNOWN
                and MissingCapability.LINE_GEOMETRY not in missing
            ):
                missing.append(MissingCapability.LINE_GEOMETRY)
            for word in line.words:
                has_words = True
                if word.geometry.status == GeometryStatus.UNKNOWN:
                    has_word_geo = False
                if not word.text:
                    has_word_text = False
                if word.confidence is None:
                    has_confidence = False

    if not has_blocks or not has_lines or not has_words:
        if not has_words:
            missing.append(MissingCapability.WORD_TEXT)
        if not has_lines:
            missing.append(MissingCapability.LINE_GEOMETRY)

    if not has_word_geo and MissingCapability.WORD_GEOMETRY not in missing:
        missing.append(MissingCapability.WORD_GEOMETRY)

    if not has_word_text and MissingCapability.WORD_TEXT not in missing:
        missing.append(MissingCapability.WORD_TEXT)

    if not has_confidence and MissingCapability.CONFIDENCE not in missing:
        missing.append(MissingCapability.CONFIDENCE)

    if not page.reading_order:
        missing.append(MissingCapability.READING_ORDER)

    level = _level_from_missing(missing, critical={
        MissingCapability.PAGE_DIMENSIONS,
        MissingCapability.WORD_TEXT,
        MissingCapability.WORD_GEOMETRY,
        MissingCapability.LINE_GEOMETRY,
    })

    return AltoReadiness(level=level, missing=missing)


def compute_page_pagexml_readiness(page: Page) -> PageXmlReadiness:
    """Compute PAGE XML readiness for a single page.

    PAGE XML is more lenient: regions + lines are often sufficient.
    Word-level geometry is nice-to-have, not required.
    """
    missing: list[MissingCapability] = []

    if page.width <= 0 or page.height <= 0:
        missing.append(MissingCapability.PAGE_DIMENSIONS)

    has_regions = len(page.text_regions) > 0
    has_lines = False

    for region in page.text_regions:
        if (
            region.geometry.status == GeometryStatus.UNKNOWN
            and MissingCapability.BLOCK_GEOMETRY not in missing
        ):
            missing.append(MissingCapability.BLOCK_GEOMETRY)
        for line in region.lines:
            has_lines = True
            if (
                line.geometry.status == GeometryStatus.UNKNOWN
                and MissingCapability.LINE_GEOMETRY not in missing
            ):
                missing.append(MissingCapability.LINE_GEOMETRY)

    if not has_regions:
        missing.append(MissingCapability.BLOCK_GEOMETRY)

    if not has_lines and MissingCapability.LINE_GEOMETRY not in missing:
        missing.append(MissingCapability.LINE_GEOMETRY)

    if not page.reading_order:
        missing.append(MissingCapability.READING_ORDER)

    level = _level_from_missing(missing, critical={
        MissingCapability.PAGE_DIMENSIONS,
        MissingCapability.BLOCK_GEOMETRY,
    })

    return PageXmlReadiness(level=level, missing=missing)


def compute_document_readiness(doc: CanonicalDocument) -> DocumentReadiness:
    """Compute overall document readiness from per-page readiness."""
    page_levels: list[ReadinessLevel] = []
    for page in doc.pages:
        alto = compute_page_alto_readiness(page)
        page_levels.append(alto.level)

    if not page_levels:
        return DocumentReadiness(level=ReadinessLevel.NONE)

    if all(lv == ReadinessLevel.FULL for lv in page_levels):
        overall = ReadinessLevel.FULL
    elif all(lv == ReadinessLevel.NONE for lv in page_levels):
        overall = ReadinessLevel.NONE
    elif any(lv == ReadinessLevel.NONE for lv in page_levels):
        overall = ReadinessLevel.DEGRADED
    else:
        overall = ReadinessLevel.PARTIAL

    return DocumentReadiness(level=overall, page_readiness=page_levels)


def _level_from_missing(
    missing: list[MissingCapability],
    critical: set[MissingCapability],
) -> ReadinessLevel:
    """Determine readiness level from missing capabilities."""
    if not missing:
        return ReadinessLevel.FULL

    has_critical = any(m in critical for m in missing)
    if has_critical:
        return ReadinessLevel.NONE

    return ReadinessLevel.PARTIAL
