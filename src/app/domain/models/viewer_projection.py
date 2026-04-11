"""ViewerProjection — the rendering truth.

This is the lightweight structure consumed by the front-end viewer.
It is derived from the CanonicalDocument by the projection builder.
It never parses XML.  It never calls providers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.app.domain.models.readiness import ExportEligibility
from src.app.domain.models.status import (
    EvidenceType,
    GeometryStatus,
    OverlayLevel,
    ReadinessLevel,
)


class OverlayItem(BaseModel):
    """A single visual overlay on the page image."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    level: OverlayLevel
    bbox: tuple[float, float, float, float] = Field(
        description="(x, y, width, height)"
    )
    polygon: list[tuple[float, float]] | None = None
    label: str | None = None
    text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance_type: EvidenceType | None = None
    geometry_status: GeometryStatus | None = None
    click_payload: dict[str, Any] | None = None


class InspectionData(BaseModel):
    """Detailed data for the inspection panel — shown on click."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    level: OverlayLevel
    text: str | None = None
    bbox: tuple[float, float, float, float]
    polygon: list[tuple[float, float]] | None = None
    confidence: float | None = None
    lang: str | None = None
    provenance_type: EvidenceType | None = None
    provenance_provider: str | None = None
    geometry_status: GeometryStatus | None = None
    readiness: ReadinessLevel | None = None
    role: str | None = None
    metadata: dict[str, Any] | None = None


class ViewerProjection(BaseModel):
    """Complete projection for the viewer — one per page."""

    model_config = ConfigDict(frozen=True)

    image_ref: str
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)

    block_overlays: list[OverlayItem] = Field(default_factory=list)
    line_overlays: list[OverlayItem] = Field(default_factory=list)
    word_overlays: list[OverlayItem] = Field(default_factory=list)
    non_text_overlays: list[OverlayItem] = Field(default_factory=list)

    inspection_index: dict[str, InspectionData] = Field(default_factory=dict)

    validation_flags: list[str] = Field(default_factory=list)
    export_status: ExportEligibility = Field(default_factory=ExportEligibility)
