"""Tests for the structural validator."""

from __future__ import annotations

from src.app.domain.models import (
    AltoReadiness,
    CanonicalDocument,
    EvidenceType,
    Geometry,
    GeometryStatus,
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
from src.app.domain.models.status import BlockRole, InputType, NonTextKind
from src.app.validators.structural_validator import validate_structure


def _prov() -> Provenance:
    return Provenance(
        provider="test", adapter="v1", source_ref="$",
        evidence_type=EvidenceType.PROVIDER_NATIVE,
    )


def _geo(x: float, y: float, w: float, h: float) -> Geometry:
    return Geometry(bbox=(x, y, w, h), status=GeometryStatus.EXACT)


def _word(wid: str, x: float, y: float, w: float, h: float) -> Word:
    return Word(id=wid, text="word", geometry=_geo(x, y, w, h), provenance=_prov())


def _line(lid: str, x: float, y: float, w: float, h: float, words: list[Word]) -> TextLine:
    return TextLine(id=lid, geometry=_geo(x, y, w, h), provenance=_prov(), words=words)


def _region(rid: str, x: float, y: float, w: float, h: float, lines: list[TextLine]) -> TextRegion:
    return TextRegion(id=rid, geometry=_geo(x, y, w, h), provenance=_prov(), lines=lines)


def _doc(regions: list[TextRegion], width: float = 1000, height: float = 1000,
         reading_order: list[str] | None = None,
         non_text: list[NonTextRegion] | None = None) -> CanonicalDocument:
    ro = reading_order if reading_order is not None else [r.id for r in regions]
    return CanonicalDocument(
        document_id="test",
        source=Source(input_type=InputType.IMAGE),
        pages=[Page(
            id="p1", page_index=0, width=width, height=height,
            alto_readiness=AltoReadiness(level=ReadinessLevel.FULL),
            page_readiness=PageXmlReadiness(level=ReadinessLevel.FULL),
            reading_order=ro,
            text_regions=regions,
            non_text_regions=non_text or [],
        )],
    )


class TestIdUniqueness:
    def test_all_unique_passes(self) -> None:
        doc = _doc([
            _region("tb1", 0, 0, 500, 200, [
                _line("tl1", 0, 0, 500, 40, [_word("w1", 0, 0, 50, 30)]),
            ]),
        ])
        report = validate_structure(doc)
        assert report.is_valid

    def test_duplicate_word_ids(self) -> None:
        doc = _doc([
            _region("tb1", 0, 0, 500, 200, [
                _line("tl1", 0, 0, 500, 40, [
                    _word("w1", 0, 0, 50, 30),
                    _word("w1", 60, 0, 50, 30),  # duplicate
                ]),
            ]),
        ])
        report = validate_structure(doc)
        assert not report.is_valid
        assert any("Duplicate ID 'w1'" in e.message for e in report.errors)

    def test_duplicate_across_levels(self) -> None:
        # line ID = region ID
        doc = _doc([
            _region("same_id", 0, 0, 500, 200, [
                _line("same_id", 0, 0, 500, 40, [_word("w1", 0, 0, 50, 30)]),
            ]),
        ])
        report = validate_structure(doc)
        assert not report.is_valid

    def test_duplicate_with_non_text_region(self) -> None:
        ntr = NonTextRegion(
            id="tb1", kind=NonTextKind.ILLUSTRATION,
            geometry=_geo(600, 0, 100, 100), provenance=_prov(),
        )
        doc = _doc(
            [_region("tb1", 0, 0, 500, 200, [
                _line("tl1", 0, 0, 500, 40, [_word("w1", 0, 0, 50, 30)]),
            ])],
            non_text=[ntr],
        )
        report = validate_structure(doc)
        assert not report.is_valid


class TestReadingOrder:
    def test_valid_references(self) -> None:
        doc = _doc([
            _region("tb1", 0, 0, 500, 200, [
                _line("tl1", 0, 0, 500, 40, [_word("w1", 0, 0, 50, 30)]),
            ]),
        ], reading_order=["tb1"])
        report = validate_structure(doc)
        assert report.is_valid

    def test_invalid_reference(self) -> None:
        doc = _doc([
            _region("tb1", 0, 0, 500, 200, [
                _line("tl1", 0, 0, 500, 40, [_word("w1", 0, 0, 50, 30)]),
            ]),
        ], reading_order=["tb1", "tb_nonexistent"])
        report = validate_structure(doc)
        assert not report.is_valid
        assert any("unknown region ID" in e.message for e in report.errors)


class TestBboxContainment:
    def test_all_contained_passes(self) -> None:
        doc = _doc([
            _region("tb1", 10, 10, 200, 100, [
                _line("tl1", 20, 20, 150, 30, [
                    _word("w1", 25, 22, 50, 25),
                ]),
            ]),
        ])
        report = validate_structure(doc)
        assert report.warning_count == 0

    def test_word_exceeds_line(self) -> None:
        doc = _doc([
            _region("tb1", 10, 10, 400, 100, [
                _line("tl1", 20, 20, 100, 30, [
                    _word("w1", 20, 20, 200, 30),  # word wider than line
                ]),
            ]),
        ])
        report = validate_structure(doc, bbox_tolerance=0)
        assert report.warning_count > 0
        assert any("word_exceeds_line" in (e.code or "") for e in report.warnings)

    def test_tolerance_allows_small_overflow(self) -> None:
        doc = _doc([
            _region("tb1", 10, 10, 200, 100, [
                _line("tl1", 20, 20, 100, 30, [
                    _word("w1", 20, 20, 103, 30),  # 3px overflow
                ]),
            ]),
        ])
        report = validate_structure(doc, bbox_tolerance=5)
        assert report.warning_count == 0

    def test_tolerance_rejects_large_overflow(self) -> None:
        doc = _doc([
            _region("tb1", 10, 10, 200, 100, [
                _line("tl1", 20, 20, 100, 30, [
                    _word("w1", 20, 20, 120, 30),  # 20px overflow
                ]),
            ]),
        ])
        report = validate_structure(doc, bbox_tolerance=5)
        assert report.warning_count > 0

    def test_region_exceeds_page(self) -> None:
        doc = _doc([
            _region("tb1", 900, 900, 200, 200, [  # exceeds 1000x1000 page
                _line("tl1", 900, 900, 100, 30, [
                    _word("w1", 900, 900, 50, 25),
                ]),
            ]),
        ], width=1000, height=1000)
        report = validate_structure(doc, bbox_tolerance=0)
        assert any("region_exceeds_page" in (e.code or "") for e in report.warnings)

    def test_line_exceeds_region(self) -> None:
        doc = _doc([
            _region("tb1", 10, 10, 100, 50, [
                _line("tl1", 10, 10, 200, 30, [  # line wider than region
                    _word("w1", 10, 10, 50, 25),
                ]),
            ]),
        ])
        report = validate_structure(doc, bbox_tolerance=0)
        assert any("line_exceeds_region" in (e.code or "") for e in report.warnings)
