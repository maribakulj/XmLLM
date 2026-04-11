"""Overlay generation — converts canonical nodes to OverlayItems."""

from __future__ import annotations

from src.app.domain.models import (
    NonTextRegion,
    TextLine,
    TextRegion,
    Word,
)
from src.app.domain.models.status import OverlayLevel
from src.app.domain.models.viewer_projection import InspectionData, OverlayItem


def word_to_overlay(word: Word) -> OverlayItem:
    """Convert a Word to an OverlayItem."""
    return OverlayItem(
        id=word.id,
        level=OverlayLevel.WORD,
        bbox=word.geometry.bbox,
        polygon=word.geometry.polygon,
        label=word.text[:30] if word.text else None,
        text=word.text,
        confidence=word.confidence,
        provenance_type=word.provenance.evidence_type,
        geometry_status=word.geometry.status,
    )


def line_to_overlay(line: TextLine) -> OverlayItem:
    """Convert a TextLine to an OverlayItem."""
    return OverlayItem(
        id=line.id,
        level=OverlayLevel.LINE,
        bbox=line.geometry.bbox,
        polygon=line.geometry.polygon,
        label=line.text[:50] if line.text else None,
        text=line.text,
        confidence=line.confidence,
        provenance_type=line.provenance.evidence_type,
        geometry_status=line.geometry.status,
    )


def region_to_overlay(region: TextRegion) -> OverlayItem:
    """Convert a TextRegion to an OverlayItem."""
    return OverlayItem(
        id=region.id,
        level=OverlayLevel.BLOCK,
        bbox=region.geometry.bbox,
        polygon=region.geometry.polygon,
        label=region.role.value if region.role else "block",
        text=region.text[:100] if region.text else None,
        confidence=region.confidence,
        provenance_type=region.provenance.evidence_type,
        geometry_status=region.geometry.status,
    )


def non_text_to_overlay(ntr: NonTextRegion) -> OverlayItem:
    """Convert a NonTextRegion to an OverlayItem."""
    return OverlayItem(
        id=ntr.id,
        level=OverlayLevel.NON_TEXT,
        bbox=ntr.geometry.bbox,
        polygon=ntr.geometry.polygon,
        label=ntr.kind.value,
        confidence=ntr.confidence,
        provenance_type=ntr.provenance.evidence_type,
        geometry_status=ntr.geometry.status,
    )


def word_to_inspection(word: Word) -> InspectionData:
    """Build inspection data for a word."""
    return InspectionData(
        id=word.id,
        level=OverlayLevel.WORD,
        text=word.text,
        bbox=word.geometry.bbox,
        polygon=word.geometry.polygon,
        confidence=word.confidence,
        lang=word.lang,
        provenance_type=word.provenance.evidence_type,
        provenance_provider=word.provenance.provider,
        geometry_status=word.geometry.status,
    )


def line_to_inspection(line: TextLine) -> InspectionData:
    """Build inspection data for a line."""
    return InspectionData(
        id=line.id,
        level=OverlayLevel.LINE,
        text=line.text,
        bbox=line.geometry.bbox,
        polygon=line.geometry.polygon,
        confidence=line.confidence,
        lang=line.lang,
        provenance_type=line.provenance.evidence_type,
        provenance_provider=line.provenance.provider,
        geometry_status=line.geometry.status,
    )


def region_to_inspection(region: TextRegion) -> InspectionData:
    """Build inspection data for a region."""
    return InspectionData(
        id=region.id,
        level=OverlayLevel.BLOCK,
        text=region.text[:200] if region.text else None,
        bbox=region.geometry.bbox,
        polygon=region.geometry.polygon,
        confidence=region.confidence,
        lang=region.lang,
        provenance_type=region.provenance.evidence_type,
        provenance_provider=region.provenance.provider,
        geometry_status=region.geometry.status,
        role=region.role.value if region.role else None,
    )
