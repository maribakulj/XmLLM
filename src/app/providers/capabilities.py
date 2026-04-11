"""Capability matrix — describes what a provider can produce."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CapabilityMatrix(BaseModel):
    """Explicit description of a provider's output capabilities.

    Used to decide which enrichers to activate, which exports to authorize,
    and how to inform the user about data completeness.
    """

    model_config = ConfigDict(frozen=True)

    block_geometry: bool = False
    line_geometry: bool = False
    word_geometry: bool = False
    polygon_geometry: bool = False
    baseline: bool = False
    reading_order: bool = False
    text_confidence: bool = False
    language: bool = False
    non_text_regions: bool = False
    tables: bool = False
    rotation_info: bool = False
