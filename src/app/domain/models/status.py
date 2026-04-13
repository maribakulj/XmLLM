"""Domain enums — single source of truth for all status and classification values.

These enums are used across the canonical document, provenance, readiness,
and viewer projection models. They carry no logic — only values.
"""

from __future__ import annotations

from enum import StrEnum

# -- Geometry ----------------------------------------------------------------


class GeometryStatus(StrEnum):
    """How a piece of geometry was obtained."""

    EXACT = "exact"
    INFERRED = "inferred"
    REPAIRED = "repaired"
    UNKNOWN = "unknown"


class CoordinateOrigin(StrEnum):
    """Origin of the coordinate system.  Always top_left in canonical model."""

    TOP_LEFT = "top_left"


class Unit(StrEnum):
    """Measurement unit.  Always px in canonical model."""

    PX = "px"


# -- Provenance --------------------------------------------------------------


class EvidenceType(StrEnum):
    """How a piece of data was produced."""

    PROVIDER_NATIVE = "provider_native"
    DERIVED = "derived"
    REPAIRED = "repaired"
    MANUAL = "manual"


# -- Document structure ------------------------------------------------------


class BlockRole(StrEnum):
    """Semantic role of a text block within the page."""

    BODY = "body"
    HEADING = "heading"
    FOOTNOTE = "footnote"
    CAPTION = "caption"
    MARGIN = "margin"
    PAGE_NUMBER = "page_number"
    HEADER = "header"
    FOOTER = "footer"
    OTHER = "other"


class NonTextKind(StrEnum):
    """Type of non-textual region."""

    ILLUSTRATION = "illustration"
    TABLE = "table"
    SEPARATOR = "separator"
    ORNAMENT = "ornament"
    GRAPHIC = "graphic"
    OTHER = "other"


# -- Source ------------------------------------------------------------------


class InputType(StrEnum):
    """Type of the original input document."""

    IMAGE = "image"
    PDF = "pdf"
    OCR_JSON = "ocr_json"
    MARKDOWN = "markdown"
    HTML = "html"
    XML = "xml"
    TEXT = "text"
    OTHER = "other"


# -- Readiness ---------------------------------------------------------------


class ReadinessLevel(StrEnum):
    """How ready a document / page / element is for export."""

    FULL = "full"
    PARTIAL = "partial"
    DEGRADED = "degraded"
    NONE = "none"


class MissingCapability(StrEnum):
    """Specific capabilities that may be missing for export readiness."""

    PAGE_DIMENSIONS = "page_dimensions"
    BLOCK_GEOMETRY = "block_geometry"
    LINE_GEOMETRY = "line_geometry"
    WORD_GEOMETRY = "word_geometry"
    WORD_TEXT = "word_text"
    READING_ORDER = "reading_order"
    LANGUAGE = "language"
    CONFIDENCE = "confidence"


# -- Overlay (viewer) --------------------------------------------------------


class OverlayLevel(StrEnum):
    """Granularity level for viewer overlays."""

    BLOCK = "block"
    LINE = "line"
    WORD = "word"
    NON_TEXT = "non_text"
