"""Readiness and export eligibility models.

These models answer: "can we export this document, and how completely?"
They are computed by validators, never set manually.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.app.domain.models.status import MissingCapability, ReadinessLevel


class AltoReadiness(BaseModel):
    """ALTO export readiness for a single page."""

    model_config = ConfigDict(frozen=True)

    level: ReadinessLevel
    missing: list[MissingCapability] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_consistency(self) -> AltoReadiness:
        if self.level == ReadinessLevel.FULL and self.missing:
            raise ValueError(
                f"level is 'full' but missing capabilities listed: {self.missing}"
            )
        if self.level == ReadinessLevel.NONE and not self.missing:
            raise ValueError("level is 'none' but no missing capabilities listed")
        return self


class PageXmlReadiness(BaseModel):
    """PAGE XML export readiness for a single page."""

    model_config = ConfigDict(frozen=True)

    level: ReadinessLevel
    missing: list[MissingCapability] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_consistency(self) -> PageXmlReadiness:
        if self.level == ReadinessLevel.FULL and self.missing:
            raise ValueError(
                f"level is 'full' but missing capabilities listed: {self.missing}"
            )
        if self.level == ReadinessLevel.NONE and not self.missing:
            raise ValueError("level is 'none' but no missing capabilities listed")
        return self


class ExportEligibility(BaseModel):
    """Aggregated export eligibility for the whole document."""

    model_config = ConfigDict(frozen=True)

    alto_export: ReadinessLevel = ReadinessLevel.NONE
    page_export: ReadinessLevel = ReadinessLevel.NONE
    viewer_render: ReadinessLevel = ReadinessLevel.NONE


class DocumentReadiness(BaseModel):
    """Global readiness summary for the document."""

    model_config = ConfigDict(frozen=True)

    level: ReadinessLevel = ReadinessLevel.NONE
    page_readiness: list[ReadinessLevel] = Field(default_factory=list)
