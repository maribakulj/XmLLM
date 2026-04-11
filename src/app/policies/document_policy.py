"""Document policy — centralised business rules for the pipeline.

This layer prevents critical decisions from being scattered across
adapters, validators, and serializers.  A policy is a named configuration
that controls what the system may or may not do.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class PolicyMode(str, Enum):
    """Named policy presets."""

    STRICT = "strict"
    STANDARD = "standard"
    PERMISSIVE = "permissive"


class DocumentPolicy(BaseModel):
    """Concrete policy controlling pipeline behaviour."""

    model_config = ConfigDict(frozen=True)

    mode: PolicyMode = PolicyMode.STANDARD

    # -- Text rules -----------------------------------------------------------
    allow_text_invention: bool = False
    """Never invent text that wasn't in the provider output."""

    # -- Geometry rules -------------------------------------------------------
    allow_polygon_to_bbox: bool = True
    """Allow deriving bbox from polygon (enricher)."""

    allow_bbox_inference: bool = True
    """Allow inferring bbox from context (e.g. line bbox from word bboxes)."""

    allow_bbox_invention: bool = False
    """Never invent bbox without any geometric basis."""

    # -- Language rules -------------------------------------------------------
    allow_lang_propagation: bool = True
    """Allow propagating language from parent to child nodes."""

    # -- Export rules ---------------------------------------------------------
    require_lines_for_alto: bool = True
    """ALTO export requires at least line-level geometry."""

    require_words_for_alto: bool = True
    """ALTO export requires word-level text and geometry."""

    allow_partial_alto: bool = True
    """Allow ALTO export with partial readiness."""

    allow_partial_page: bool = True
    """Allow PAGE export with partial readiness."""

    # -- Enricher rules -------------------------------------------------------
    allow_reading_order_inference: bool = True
    """Allow inferring reading order from spatial position."""

    allow_hyphenation_detection: bool = True
    """Allow detecting word hyphenation at line boundaries."""

    # -- Tolerance ------------------------------------------------------------
    bbox_containment_tolerance: float = 5.0
    """Pixels of allowed overflow for bbox containment checks."""

    @property
    def strict_mode(self) -> bool:
        return self.mode == PolicyMode.STRICT


def strict_policy() -> DocumentPolicy:
    """A strict policy: no inference, no partial exports."""
    return DocumentPolicy(
        mode=PolicyMode.STRICT,
        allow_polygon_to_bbox=False,
        allow_bbox_inference=False,
        allow_lang_propagation=False,
        allow_partial_alto=False,
        allow_partial_page=False,
        allow_reading_order_inference=False,
        allow_hyphenation_detection=False,
    )


def permissive_policy() -> DocumentPolicy:
    """A permissive policy: allow inference and partial exports."""
    return DocumentPolicy(
        mode=PolicyMode.PERMISSIVE,
        allow_bbox_inference=True,
        allow_partial_alto=True,
        allow_partial_page=True,
        bbox_containment_tolerance=10.0,
    )
