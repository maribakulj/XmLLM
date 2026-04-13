"""Tests for the CanonicalBuilder."""

from __future__ import annotations

import pytest
from src.app.domain.models import (
    EvidenceType,
    Geometry,
    GeometryStatus,
    Provenance,
)
from src.app.domain.models.status import BlockRole, InputType
from src.app.normalization.canonical_builder import CanonicalBuilder


def _geo() -> Geometry:
    return Geometry(bbox=(100, 200, 300, 50), status=GeometryStatus.EXACT)


def _prov(ref: str = "$.test") -> Provenance:
    return Provenance(
        provider="test",
        adapter="test.v1",
        source_ref=ref,
        evidence_type=EvidenceType.PROVIDER_NATIVE,
    )


class TestCanonicalBuilder:
    def test_minimal_document(self) -> None:
        builder = CanonicalBuilder("doc1", InputType.IMAGE, "test.png")
        page = builder.add_page("p1", 0, 2480, 3508)
        region = page.add_text_region("tb1", _geo(), _prov(), role=BlockRole.BODY)
        line = region.add_line("tl1", _geo(), _prov())
        line.add_word("w1", "Hello", _geo(), _prov(), confidence=0.95)

        doc = builder.build()
        assert doc.document_id == "doc1"
        assert len(doc.pages) == 1
        assert len(doc.pages[0].text_regions) == 1
        assert doc.pages[0].text_regions[0].lines[0].words[0].text == "Hello"

    def test_reading_order_auto_built(self) -> None:
        builder = CanonicalBuilder("doc1", InputType.IMAGE)
        page = builder.add_page("p1", 0, 100, 100)
        page.add_text_region("tb1", _geo(), _prov()).\
            add_line("tl1", _geo(), _prov()).\
            add_word("w1", "A", _geo(), _prov())
        page.add_text_region("tb2", _geo(), _prov()).\
            add_line("tl2", _geo(), _prov()).\
            add_word("w2", "B", _geo(), _prov())

        doc = builder.build()
        assert doc.pages[0].reading_order == ["tb1", "tb2"]

    def test_no_pages_raises(self) -> None:
        builder = CanonicalBuilder("doc1", InputType.IMAGE)
        with pytest.raises(ValueError, match="at least one page"):
            builder.build()

    def test_empty_region_raises(self) -> None:
        builder = CanonicalBuilder("doc1", InputType.IMAGE)
        page = builder.add_page("p1", 0, 100, 100)
        page.add_text_region("tb1", _geo(), _prov())
        with pytest.raises(ValueError, match="no lines"):
            builder.build()

    def test_empty_line_raises(self) -> None:
        builder = CanonicalBuilder("doc1", InputType.IMAGE)
        page = builder.add_page("p1", 0, 100, 100)
        region = page.add_text_region("tb1", _geo(), _prov())
        region.add_line("tl1", _geo(), _prov())
        with pytest.raises(ValueError, match="no words"):
            builder.build()

    def test_multiple_words_per_line(self) -> None:
        builder = CanonicalBuilder("doc1", InputType.IMAGE)
        page = builder.add_page("p1", 0, 1000, 1000)
        region = page.add_text_region("tb1", _geo(), _prov())
        line = region.add_line("tl1", _geo(), _prov())
        line.add_word("w1", "Hello", _geo(), _prov())
        line.add_word("w2", "world", _geo(), _prov())

        doc = builder.build()
        assert len(doc.pages[0].text_regions[0].lines[0].words) == 2
        assert doc.pages[0].text_regions[0].lines[0].text == "Hello world"

    def test_with_metadata(self) -> None:
        builder = CanonicalBuilder(
            "doc1", InputType.IMAGE, metadata={"project": "test"}
        )
        page = builder.add_page("p1", 0, 100, 100)
        page.set_metadata({"page_quality": "good"})
        region = page.add_text_region("tb1", _geo(), _prov())
        line = region.add_line("tl1", _geo(), _prov())
        line.add_word("w1", "ok", _geo(), _prov(), metadata={"custom": True})

        doc = builder.build()
        assert doc.metadata == {"project": "test"}
        assert doc.pages[0].metadata == {"page_quality": "good"}
        assert doc.pages[0].text_regions[0].lines[0].words[0].metadata == {"custom": True}
