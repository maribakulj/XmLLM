"""Tests for the CanonicalDocument model — the heart of the system."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from src.app.domain.models import (
    AltoReadiness,
    Audit,
    BlockRole,
    CanonicalDocument,
    EvidenceType,
    Geometry,
    GeometryStatus,
    Hyphenation,
    InputType,
    NonTextKind,
    NonTextRegion,
    Page,
    PageXmlReadiness,
    Provenance,
    ReadinessLevel,
    Source,
    TextLine,
    TextRegion,
    Word,
)

# -- Helpers (reusable fixture builders) -------------------------------------


def _prov(ref: str = "$.test", evidence: EvidenceType = EvidenceType.PROVIDER_NATIVE) -> Provenance:
    return Provenance(
        provider="test-provider",
        adapter="adapter.test.v1",
        source_ref=ref,
        evidence_type=evidence,
    )


def _geo(
    x: float = 100,
    y: float = 200,
    w: float = 300,
    h: float = 50,
    status: GeometryStatus = GeometryStatus.EXACT,
) -> Geometry:
    return Geometry(bbox=(x, y, w, h), status=status)


def _word(
    id: str = "w1",
    text: str = "Bonjour",
    x: float = 100,
    y: float = 200,
    w: float = 90,
    h: float = 40,
) -> Word:
    return Word(
        id=id,
        text=text,
        geometry=_geo(x, y, w, h),
        lang="fra",
        confidence=0.96,
        provenance=_prov(f"$.words.{id}"),
    )


def _line(id: str = "tl1", words: list[Word] | None = None) -> TextLine:
    return TextLine(
        id=id,
        geometry=_geo(100, 200, 1100, 42),
        lang="fra",
        provenance=_prov(f"$.lines.{id}"),
        words=words or [_word()],
    )


def _region(id: str = "tb1", lines: list[TextLine] | None = None) -> TextRegion:
    return TextRegion(
        id=id,
        role=BlockRole.BODY,
        geometry=_geo(100, 200, 1200, 900),
        lang="fra",
        provenance=_prov(f"$.blocks.{id}"),
        lines=lines or [_line()],
    )


def _page(
    id: str = "p1",
    text_regions: list[TextRegion] | None = None,
) -> Page:
    return Page(
        id=id,
        page_index=0,
        width=2480,
        height=3508,
        alto_readiness=AltoReadiness(level=ReadinessLevel.FULL),
        page_readiness=PageXmlReadiness(level=ReadinessLevel.FULL),
        reading_order=["tb1"],
        text_regions=text_regions or [_region()],
    )


def _doc(pages: list[Page] | None = None) -> CanonicalDocument:
    return CanonicalDocument(
        document_id="doc_test_001",
        source=Source(input_type=InputType.IMAGE, filename="test.png"),
        pages=pages or [_page()],
    )


# -- Source ------------------------------------------------------------------


class TestSource:
    def test_minimal(self) -> None:
        s = Source(input_type=InputType.IMAGE)
        assert s.filename is None
        assert s.checksum is None

    def test_full(self) -> None:
        s = Source(
            input_type=InputType.IMAGE,
            filename="page.tif",
            mime_type="image/tiff",
            checksum="abc123",
        )
        assert s.filename == "page.tif"


# -- Hyphenation -------------------------------------------------------------


class TestHyphenation:
    def test_not_hyphenated(self) -> None:
        h = Hyphenation(is_hyphenated=False)
        assert h.part is None
        assert h.full_form is None

    def test_part_1(self) -> None:
        h = Hyphenation(is_hyphenated=True, part=1, full_form="patrimoine")
        assert h.part == 1

    def test_part_2(self) -> None:
        h = Hyphenation(is_hyphenated=True, part=2, full_form="patrimoine")
        assert h.part == 2

    def test_false_with_part_rejected(self) -> None:
        with pytest.raises(ValidationError, match="is_hyphenated is False"):
            Hyphenation(is_hyphenated=False, part=1, full_form="test")

    def test_true_without_part_rejected(self) -> None:
        with pytest.raises(ValidationError, match="part must be 1 or 2"):
            Hyphenation(is_hyphenated=True, part=None, full_form="test")

    def test_true_without_full_form_rejected(self) -> None:
        with pytest.raises(ValidationError, match="full_form is required"):
            Hyphenation(is_hyphenated=True, part=1, full_form=None)

    def test_invalid_part_rejected(self) -> None:
        with pytest.raises(ValidationError, match="part must be 1 or 2"):
            Hyphenation(is_hyphenated=True, part=3, full_form="test")


# -- Word --------------------------------------------------------------------


class TestWord:
    def test_valid(self) -> None:
        w = _word()
        assert w.text == "Bonjour"
        assert w.confidence == 0.96

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Word(
                id="w1",
                text="",
                geometry=_geo(),
                provenance=_prov(),
            )

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Word(
                id="",
                text="hello",
                geometry=_geo(),
                provenance=_prov(),
            )

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Word(
                id="w1",
                text="hello",
                geometry=_geo(),
                confidence=1.5,
                provenance=_prov(),
            )

    def test_invalid_lang_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Word(
                id="w1",
                text="hello",
                geometry=_geo(),
                lang="french",  # must be 3-letter ISO
                provenance=_prov(),
            )

    def test_valid_lang(self) -> None:
        w = Word(
            id="w1",
            text="hello",
            geometry=_geo(),
            lang="eng",
            provenance=_prov(),
        )
        assert w.lang == "eng"

    def test_null_confidence_ok(self) -> None:
        w = Word(
            id="w1",
            text="hello",
            geometry=_geo(),
            confidence=None,
            provenance=_prov(),
        )
        assert w.confidence is None

    def test_with_hyphenation(self) -> None:
        w = Word(
            id="w1",
            text="patri-",
            geometry=_geo(),
            provenance=_prov(),
            hyphenation=Hyphenation(is_hyphenated=True, part=1, full_form="patrimoine"),
        )
        assert w.hyphenation is not None
        assert w.hyphenation.full_form == "patrimoine"

    def test_with_metadata(self) -> None:
        w = Word(
            id="w1",
            text="hello",
            geometry=_geo(),
            provenance=_prov(),
            metadata={"custom_field": "value"},
        )
        assert w.metadata == {"custom_field": "value"}


# -- TextLine ----------------------------------------------------------------


class TestTextLine:
    def test_valid(self) -> None:
        line = _line()
        assert line.text == "Bonjour"

    def test_empty_words_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TextLine(
                id="tl1",
                geometry=_geo(),
                provenance=_prov(),
                words=[],
            )

    def test_multiple_words(self) -> None:
        line = _line(words=[_word("w1", "Hello"), _word("w2", "world")])
        assert line.text == "Hello world"


# -- TextRegion --------------------------------------------------------------


class TestTextRegion:
    def test_valid(self) -> None:
        r = _region()
        assert r.role == BlockRole.BODY
        assert "Bonjour" in r.text

    def test_empty_lines_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TextRegion(
                id="tb1",
                geometry=_geo(),
                provenance=_prov(),
                lines=[],
            )

    def test_multiple_lines(self) -> None:
        r = _region(
            lines=[
                _line("tl1", [_word("w1", "First")]),
                _line("tl2", [_word("w2", "Second")]),
            ]
        )
        assert r.text == "First\nSecond"

    def test_null_role(self) -> None:
        r = TextRegion(
            id="tb1",
            role=None,
            geometry=_geo(),
            provenance=_prov(),
            lines=[_line()],
        )
        assert r.role is None


# -- NonTextRegion -----------------------------------------------------------


class TestNonTextRegion:
    def test_valid(self) -> None:
        ntr = NonTextRegion(
            id="ntr1",
            kind=NonTextKind.ILLUSTRATION,
            geometry=_geo(),
            provenance=_prov(),
        )
        assert ntr.kind == NonTextKind.ILLUSTRATION

    def test_all_kinds(self) -> None:
        for kind in NonTextKind:
            ntr = NonTextRegion(
                id=f"ntr_{kind.value}",
                kind=kind,
                geometry=_geo(),
                provenance=_prov(),
            )
            assert ntr.kind == kind


# -- Page --------------------------------------------------------------------


class TestPage:
    def test_valid(self) -> None:
        p = _page()
        assert p.width == 2480
        assert p.height == 3508
        assert "Bonjour" in p.text

    def test_zero_width_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Page(
                id="p1",
                page_index=0,
                width=0,
                height=100,
            )

    def test_negative_index_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Page(
                id="p1",
                page_index=-1,
                width=100,
                height=100,
            )

    def test_empty_page_ok(self) -> None:
        """A page with no regions is valid (e.g. blank page)."""
        p = Page(
            id="p1",
            page_index=0,
            width=2480,
            height=3508,
        )
        assert p.text_regions == []
        assert p.text == ""

    def test_with_non_text_region(self) -> None:
        ntr = NonTextRegion(
            id="ntr1",
            kind=NonTextKind.SEPARATOR,
            geometry=_geo(),
            provenance=_prov(),
        )
        p = Page(
            id="p1",
            page_index=0,
            width=2480,
            height=3508,
            non_text_regions=[ntr],
        )
        assert len(p.non_text_regions) == 1


# -- CanonicalDocument -------------------------------------------------------


class TestCanonicalDocument:
    def test_valid_minimal(self) -> None:
        doc = _doc()
        assert doc.document_id == "doc_test_001"
        assert doc.schema_version == "1.0.0"
        assert len(doc.pages) == 1

    def test_empty_pages_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalDocument(
                document_id="doc1",
                source=Source(input_type=InputType.IMAGE),
                pages=[],
            )

    def test_text_property(self) -> None:
        doc = _doc()
        assert "Bonjour" in doc.text

    def test_all_ids(self) -> None:
        doc = _doc()
        ids = doc.all_ids
        assert "p1" in ids
        assert "tb1" in ids
        assert "tl1" in ids
        assert "w1" in ids

    def test_all_text_region_ids(self) -> None:
        doc = _doc()
        assert doc.all_text_region_ids == {"tb1"}

    def test_invalid_schema_version_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalDocument(
                schema_version="v1",
                document_id="doc1",
                source=Source(input_type=InputType.IMAGE),
                pages=[_page()],
            )

    def test_empty_document_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalDocument(
                document_id="",
                source=Source(input_type=InputType.IMAGE),
                pages=[_page()],
            )

    def test_default_audit(self) -> None:
        doc = _doc()
        assert doc.audit.enrichers_applied == []
        assert doc.audit.validators_run == []

    def test_with_audit(self) -> None:
        doc = CanonicalDocument(
            document_id="doc1",
            source=Source(input_type=InputType.IMAGE),
            pages=[_page()],
            audit=Audit(
                provider_id="paddle",
                runtime_type="local",
                enrichers_applied=["polygon_to_bbox", "lang_propagation"],
            ),
        )
        assert len(doc.audit.enrichers_applied) == 2

    def test_default_export_eligibility(self) -> None:
        doc = _doc()
        assert doc.export_eligibility.alto_export == ReadinessLevel.NONE

    def test_with_metadata(self) -> None:
        doc = CanonicalDocument(
            document_id="doc1",
            source=Source(input_type=InputType.IMAGE),
            pages=[_page()],
            metadata={"project": "test", "version": 2},
        )
        assert doc.metadata["project"] == "test"

    def test_json_roundtrip(self) -> None:
        """Full serialization → deserialization cycle."""
        doc = _doc()
        json_str = doc.model_dump_json()
        parsed = json.loads(json_str)
        doc2 = CanonicalDocument.model_validate(parsed)
        assert doc2.document_id == doc.document_id
        assert len(doc2.pages) == len(doc.pages)
        assert doc2.pages[0].text_regions[0].lines[0].words[0].text == "Bonjour"

    def test_json_schema_generation(self) -> None:
        """Verify we can generate a JSON Schema from the Pydantic model."""
        schema = CanonicalDocument.model_json_schema()
        assert schema["title"] == "CanonicalDocument"
        assert "pages" in schema["properties"]
        # Verify nested definitions exist
        assert "$defs" in schema
        defs = schema["$defs"]
        assert "Word" in defs
        assert "TextLine" in defs
        assert "TextRegion" in defs
        assert "Page" in defs
        assert "Geometry" in defs
        assert "Provenance" in defs


# -- Full example from spec --------------------------------------------------


class TestSpecExample:
    """Validate the example from the architecture document §14."""

    def test_spec_example_validates(self) -> None:
        doc = CanonicalDocument(
            schema_version="1.0.0",
            document_id="doc_0001",
            source=Source(
                input_type=InputType.IMAGE,
                filename="page_001.tif",
                mime_type="image/tiff",
                checksum=None,
            ),
            pages=[
                Page(
                    id="p1",
                    page_index=0,
                    width=2480,
                    height=3508,
                    alto_readiness=AltoReadiness(level=ReadinessLevel.FULL),
                    page_readiness=PageXmlReadiness(level=ReadinessLevel.FULL),
                    reading_order=["tb1"],
                    text_regions=[
                        TextRegion(
                            id="tb1",
                            role=BlockRole.BODY,
                            geometry=Geometry(
                                bbox=(100, 200, 1200, 900),
                                polygon=None,
                                status=GeometryStatus.EXACT,
                            ),
                            confidence=None,
                            lang="fra",
                            provenance=Provenance(
                                provider="paddleocr-vl",
                                adapter="adapter.paddle.v1",
                                source_ref="$.pages[0].blocks[0]",
                                evidence_type=EvidenceType.PROVIDER_NATIVE,
                                derived_from=[],
                            ),
                            lines=[
                                TextLine(
                                    id="tl1",
                                    geometry=Geometry(
                                        bbox=(110, 220, 1180, 42),
                                        polygon=None,
                                        status=GeometryStatus.EXACT,
                                    ),
                                    confidence=None,
                                    lang="fra",
                                    provenance=Provenance(
                                        provider="paddleocr-vl",
                                        adapter="adapter.paddle.v1",
                                        source_ref="$.pages[0].blocks[0].lines[0]",
                                        evidence_type=EvidenceType.PROVIDER_NATIVE,
                                        derived_from=[],
                                    ),
                                    words=[
                                        Word(
                                            id="w1",
                                            text="Bonjour",
                                            normalized_text=None,
                                            geometry=Geometry(
                                                bbox=(110, 220, 90, 40),
                                                polygon=None,
                                                status=GeometryStatus.EXACT,
                                            ),
                                            lang="fra",
                                            confidence=0.96,
                                            style_refs=[],
                                            hyphenation=None,
                                            provenance=Provenance(
                                                provider="paddleocr-vl",
                                                adapter="adapter.paddle.v1",
                                                source_ref="$.pages[0].blocks[0].lines[0].words[0]",
                                                evidence_type=EvidenceType.PROVIDER_NATIVE,
                                                derived_from=[],
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                    non_text_regions=[],
                ),
            ],
        )
        assert doc.document_id == "doc_0001"
        assert doc.pages[0].text_regions[0].lines[0].words[0].text == "Bonjour"
        assert doc.pages[0].text_regions[0].lines[0].words[0].confidence == 0.96

    def test_hyphenation_example(self) -> None:
        """Validate the hyphenation example from §8."""
        w1 = Word(
            id="w18",
            text="patri-",
            geometry=_geo(500, 800, 95, 30),
            confidence=0.89,
            lang="fra",
            provenance=_prov("$.blocks[2].lines[5].words[7]"),
            hyphenation=Hyphenation(is_hyphenated=True, part=1, full_form="patrimoine"),
        )
        w2 = Word(
            id="w19",
            text="moine",
            geometry=_geo(120, 840, 70, 30),
            confidence=0.90,
            lang="fra",
            provenance=_prov("$.blocks[2].lines[6].words[0]"),
            hyphenation=Hyphenation(is_hyphenated=True, part=2, full_form="patrimoine"),
        )
        assert w1.hyphenation.full_form == w2.hyphenation.full_form == "patrimoine"
        assert w1.hyphenation.part == 1
        assert w2.hyphenation.part == 2
