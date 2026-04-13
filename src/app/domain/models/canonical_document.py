"""CanonicalDocument — the business truth of the system.

This is the central model.  Everything flows through it:
  Provider output → Adapter → CanonicalDocument → Validators → Serializers

The hierarchy is:  Document → Page → TextRegion (block) → TextLine → Word
                                    → NonTextRegion

Every node carries geometry + provenance.  No exceptions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.app.domain.models.geometry import Geometry
from src.app.domain.models.provenance import Provenance
from src.app.domain.models.readiness import (
    AltoReadiness,
    DocumentReadiness,
    ExportEligibility,
    PageXmlReadiness,
)
from src.app.domain.models.status import (
    BlockRole,
    CoordinateOrigin,
    InputType,
    NonTextKind,
    ReadinessLevel,
    Unit,
)


# -- Source ------------------------------------------------------------------


class Source(BaseModel):
    """Metadata about the original input document."""

    model_config = ConfigDict(frozen=True)

    input_type: InputType
    filename: str | None = None
    mime_type: str | None = None
    checksum: str | None = None


# -- Hyphenation -------------------------------------------------------------


class Hyphenation(BaseModel):
    """Word-level hyphenation info for split words across lines."""

    model_config = ConfigDict(frozen=True)

    is_hyphenated: bool
    part: int | None = None
    full_form: str | None = None

    @model_validator(mode="after")
    def _validate_consistency(self) -> Hyphenation:
        if not self.is_hyphenated:
            if self.part is not None or self.full_form is not None:
                raise ValueError(
                    "When is_hyphenated is False, part and full_form must be None"
                )
        else:
            if self.part not in (1, 2):
                raise ValueError(f"Hyphenation part must be 1 or 2, got {self.part}")
            if not self.full_form:
                raise ValueError("Hyphenation full_form is required when is_hyphenated is True")
        return self


# -- Word --------------------------------------------------------------------


class Word(BaseModel):
    """A single word — the leaf level of the canonical hierarchy.

    This is the primary unit for ALTO export (maps to <String>).
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    normalized_text: str | None = None
    geometry: Geometry
    lang: str | None = Field(default=None, pattern=r"^[a-z]{3}$")
    confidence: float | None = Field(default=None, ge=0, le=1)
    style_refs: list[str] = Field(default_factory=list)
    hyphenation: Hyphenation | None = None
    provenance: Provenance
    metadata: dict[str, Any] | None = None


# -- TextLine ----------------------------------------------------------------


class TextLine(BaseModel):
    """A line of text — contains an ordered list of Words.

    Maps to <TextLine> in ALTO and PAGE XML.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    geometry: Geometry
    confidence: float | None = Field(default=None, ge=0, le=1)
    lang: str | None = Field(default=None, pattern=r"^[a-z]{3}$")
    provenance: Provenance
    words: list[Word] = Field(min_length=1)
    metadata: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        """Concatenated text of all words in this line."""
        return " ".join(w.text for w in self.words)


# -- TextRegion (block) ------------------------------------------------------


class TextRegion(BaseModel):
    """A text block / region — contains an ordered list of TextLines.

    Maps to <TextBlock> in ALTO and <TextRegion> in PAGE XML.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    role: BlockRole | None = None
    geometry: Geometry
    confidence: float | None = Field(default=None, ge=0, le=1)
    lang: str | None = Field(default=None, pattern=r"^[a-z]{3}$")
    provenance: Provenance
    lines: list[TextLine] = Field(min_length=1)
    metadata: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        """Concatenated text of all lines in this region."""
        return "\n".join(line.text for line in self.lines)


# -- NonTextRegion -----------------------------------------------------------


class NonTextRegion(BaseModel):
    """A non-textual region (illustration, table, separator, etc.)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    kind: NonTextKind
    geometry: Geometry
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance: Provenance
    metadata: dict[str, Any] | None = None


# -- Page --------------------------------------------------------------------


class Page(BaseModel):
    """A single page in the document.

    Contains text regions (blocks), non-text regions, reading order,
    and per-page readiness assessments.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    page_index: int = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    unit: Unit = Unit.PX
    rotation: float = 0.0
    coordinate_origin: CoordinateOrigin = CoordinateOrigin.TOP_LEFT

    alto_readiness: AltoReadiness = Field(
        default_factory=lambda: AltoReadiness(level=ReadinessLevel.NONE, missing=["word_text"])
    )
    page_readiness: PageXmlReadiness = Field(
        default_factory=lambda: PageXmlReadiness(level=ReadinessLevel.NONE, missing=["word_text"])
    )

    reading_order: list[str] = Field(default_factory=list)

    text_regions: list[TextRegion] = Field(default_factory=list)
    non_text_regions: list[NonTextRegion] = Field(default_factory=list)

    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        """Concatenated text of all text regions."""
        return "\n\n".join(r.text for r in self.text_regions)


# -- Audit -------------------------------------------------------------------


class Audit(BaseModel):
    """Audit trail for the document processing pipeline."""

    model_config = ConfigDict(frozen=True)

    provider_id: str | None = None
    runtime_type: str | None = None
    adapter_version: str | None = None
    enrichers_applied: list[str] = Field(default_factory=list)
    validators_run: list[str] = Field(default_factory=list)
    processing_duration_ms: float | None = None
    warnings: list[str] = Field(default_factory=list)


# -- CanonicalDocument -------------------------------------------------------


class CanonicalDocument(BaseModel):
    """The canonical document — business truth of the system.

    This is the single representation that all validators, enrichers,
    and serializers operate on.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    document_id: str = Field(min_length=1)
    source: Source
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    pages: list[Page] = Field(min_length=1)

    audit: Audit = Field(default_factory=Audit)
    global_readiness: DocumentReadiness = Field(default_factory=DocumentReadiness)
    export_eligibility: ExportEligibility = Field(default_factory=ExportEligibility)

    metadata: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        """Concatenated text of all pages."""
        return "\n\n---\n\n".join(p.text for p in self.pages)

    @property
    def all_text_region_ids(self) -> set[str]:
        """All text region IDs across all pages."""
        return {r.id for p in self.pages for r in p.text_regions}

    @property
    def all_ids(self) -> set[str]:
        """Every node ID in the document (pages, regions, lines, words)."""
        ids: set[str] = set()
        for page in self.pages:
            ids.add(page.id)
            for region in page.text_regions:
                ids.add(region.id)
                for line in region.lines:
                    ids.add(line.id)
                    for word in line.words:
                        ids.add(word.id)
            for ntr in page.non_text_regions:
                ids.add(ntr.id)
        return ids
