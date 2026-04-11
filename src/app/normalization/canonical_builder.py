"""CanonicalBuilder — builder pattern for constructing CanonicalDocuments.

Usage:
    builder = CanonicalBuilder("doc_001", InputType.IMAGE, "page.png")
    page = builder.add_page(page_id="p1", width=2480, height=3508)
    region = page.add_text_region("tb1", geometry=geo, provenance=prov)
    line = region.add_line("tl1", geometry=geo, provenance=prov)
    line.add_word("w1", text="Hello", geometry=geo, provenance=prov, confidence=0.95)
    doc = builder.build()
"""

from __future__ import annotations

from typing import Any

from src.app.domain.models import (
    AltoReadiness,
    CanonicalDocument,
    Geometry,
    Hyphenation,
    NonTextRegion,
    Page,
    PageXmlReadiness,
    Provenance,
    Source,
    TextLine,
    TextRegion,
    Word,
)
from src.app.domain.models.status import (
    BlockRole,
    InputType,
    NonTextKind,
    ReadinessLevel,
)


class WordBuilder:
    """Accumulates word data before the line is finalized."""

    def __init__(
        self,
        word_id: str,
        text: str,
        geometry: Geometry,
        provenance: Provenance,
        *,
        confidence: float | None = None,
        lang: str | None = None,
        hyphenation: Hyphenation | None = None,
        normalized_text: str | None = None,
        style_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._data = {
            "id": word_id,
            "text": text,
            "geometry": geometry,
            "provenance": provenance,
            "confidence": confidence,
            "lang": lang,
            "hyphenation": hyphenation,
            "normalized_text": normalized_text,
            "style_refs": style_refs or [],
            "metadata": metadata,
        }

    def build(self) -> Word:
        return Word(**self._data)


class LineBuilder:
    """Accumulates words for a single line."""

    def __init__(
        self,
        line_id: str,
        geometry: Geometry,
        provenance: Provenance,
        *,
        confidence: float | None = None,
        lang: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._line_id = line_id
        self._geometry = geometry
        self._provenance = provenance
        self._confidence = confidence
        self._lang = lang
        self._metadata = metadata
        self._words: list[WordBuilder] = []

    def add_word(
        self,
        word_id: str,
        text: str,
        geometry: Geometry,
        provenance: Provenance,
        *,
        confidence: float | None = None,
        lang: str | None = None,
        hyphenation: Hyphenation | None = None,
        normalized_text: str | None = None,
        style_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WordBuilder:
        wb = WordBuilder(
            word_id,
            text,
            geometry,
            provenance,
            confidence=confidence,
            lang=lang,
            hyphenation=hyphenation,
            normalized_text=normalized_text,
            style_refs=style_refs,
            metadata=metadata,
        )
        self._words.append(wb)
        return wb

    def build(self) -> TextLine:
        if not self._words:
            raise ValueError(f"Line {self._line_id} has no words")
        return TextLine(
            id=self._line_id,
            geometry=self._geometry,
            provenance=self._provenance,
            confidence=self._confidence,
            lang=self._lang,
            words=[w.build() for w in self._words],
            metadata=self._metadata,
        )


class RegionBuilder:
    """Accumulates lines for a text region (block)."""

    def __init__(
        self,
        region_id: str,
        geometry: Geometry,
        provenance: Provenance,
        *,
        role: BlockRole | None = None,
        confidence: float | None = None,
        lang: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._region_id = region_id
        self._geometry = geometry
        self._provenance = provenance
        self._role = role
        self._confidence = confidence
        self._lang = lang
        self._metadata = metadata
        self._lines: list[LineBuilder] = []

    def add_line(
        self,
        line_id: str,
        geometry: Geometry,
        provenance: Provenance,
        *,
        confidence: float | None = None,
        lang: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LineBuilder:
        lb = LineBuilder(
            line_id,
            geometry,
            provenance,
            confidence=confidence,
            lang=lang,
            metadata=metadata,
        )
        self._lines.append(lb)
        return lb

    def build(self) -> TextRegion:
        if not self._lines:
            raise ValueError(f"Region {self._region_id} has no lines")
        return TextRegion(
            id=self._region_id,
            role=self._role,
            geometry=self._geometry,
            provenance=self._provenance,
            confidence=self._confidence,
            lang=self._lang,
            lines=[ln.build() for ln in self._lines],
            metadata=self._metadata,
        )


class PageBuilder:
    """Accumulates regions for a single page."""

    def __init__(
        self,
        page_id: str,
        page_index: int,
        width: float,
        height: float,
    ) -> None:
        self._page_id = page_id
        self._page_index = page_index
        self._width = width
        self._height = height
        self._text_regions: list[RegionBuilder] = []
        self._non_text_regions: list[NonTextRegion] = []
        self._reading_order: list[str] = []
        self._warnings: list[str] = []
        self._metadata: dict[str, Any] | None = None

    def add_text_region(
        self,
        region_id: str,
        geometry: Geometry,
        provenance: Provenance,
        *,
        role: BlockRole | None = None,
        confidence: float | None = None,
        lang: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RegionBuilder:
        rb = RegionBuilder(
            region_id,
            geometry,
            provenance,
            role=role,
            confidence=confidence,
            lang=lang,
            metadata=metadata,
        )
        self._text_regions.append(rb)
        self._reading_order.append(region_id)
        return rb

    def add_non_text_region(
        self,
        region_id: str,
        kind: NonTextKind,
        geometry: Geometry,
        provenance: Provenance,
        *,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._non_text_regions.append(
            NonTextRegion(
                id=region_id,
                kind=kind,
                geometry=geometry,
                provenance=provenance,
                confidence=confidence,
                metadata=metadata,
            )
        )

    def add_warning(self, warning: str) -> None:
        self._warnings.append(warning)

    def set_metadata(self, metadata: dict[str, Any]) -> None:
        self._metadata = metadata

    def build(self) -> Page:
        return Page(
            id=self._page_id,
            page_index=self._page_index,
            width=self._width,
            height=self._height,
            alto_readiness=AltoReadiness(
                level=ReadinessLevel.NONE, missing=["word_text"]
            ),
            page_readiness=PageXmlReadiness(
                level=ReadinessLevel.NONE, missing=["word_text"]
            ),
            reading_order=self._reading_order,
            text_regions=[r.build() for r in self._text_regions],
            non_text_regions=self._non_text_regions,
            warnings=self._warnings,
            metadata=self._metadata,
        )


class CanonicalBuilder:
    """Top-level builder for constructing a CanonicalDocument."""

    def __init__(
        self,
        document_id: str,
        input_type: InputType,
        filename: str | None = None,
        *,
        mime_type: str | None = None,
        checksum: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._document_id = document_id
        self._source = Source(
            input_type=input_type,
            filename=filename,
            mime_type=mime_type,
            checksum=checksum,
        )
        self._pages: list[PageBuilder] = []
        self._metadata = metadata

    def add_page(
        self,
        page_id: str,
        page_index: int,
        width: float,
        height: float,
    ) -> PageBuilder:
        pb = PageBuilder(page_id, page_index, width, height)
        self._pages.append(pb)
        return pb

    def build(self) -> CanonicalDocument:
        """Build and validate the CanonicalDocument.

        Raises pydantic.ValidationError if the resulting document is invalid.
        """
        if not self._pages:
            raise ValueError("Document must have at least one page")
        return CanonicalDocument(
            document_id=self._document_id,
            source=self._source,
            pages=[p.build() for p in self._pages],
            metadata=self._metadata,
        )
