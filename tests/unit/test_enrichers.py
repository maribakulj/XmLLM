"""Tests for all enrichers and the enricher pipeline."""

from __future__ import annotations

from src.app.domain.models import (
    CanonicalDocument,
    EvidenceType,
    Geometry,
    GeometryStatus,
    Hyphenation,
    Page,
    Provenance,
    Source,
    TextLine,
    TextRegion,
    Word,
)
from src.app.domain.models.status import InputType
from src.app.enrichers import EnricherPipeline
from src.app.enrichers.bbox_repair_light import BboxRepairLightEnricher
from src.app.enrichers.hyphenation_basic import HyphenationBasicEnricher
from src.app.enrichers.lang_propagation import LangPropagationEnricher
from src.app.enrichers.polygon_to_bbox import PolygonToBboxEnricher
from src.app.enrichers.reading_order_simple import ReadingOrderSimpleEnricher
from src.app.enrichers.text_consistency import TextConsistencyEnricher
from src.app.policies.document_policy import DocumentPolicy, strict_policy

# -- Helpers ------------------------------------------------------------------


def _prov() -> Provenance:
    return Provenance(
        provider="test", adapter="v1", source_ref="$",
        evidence_type=EvidenceType.PROVIDER_NATIVE,
    )


def _geo(x: float = 10, y: float = 10, w: float = 100, h: float = 30,
         status: GeometryStatus = GeometryStatus.EXACT,
         polygon: list[tuple[float, float]] | None = None) -> Geometry:
    return Geometry(bbox=(x, y, w, h), polygon=polygon, status=status)


def _word(wid: str, text: str, x: float = 10, y: float = 10, w: float = 50, h: float = 25,
          lang: str | None = None, confidence: float | None = None,
          status: GeometryStatus = GeometryStatus.EXACT,
          polygon: list[tuple[float, float]] | None = None,
          hyphenation: Hyphenation | None = None) -> Word:
    return Word(
        id=wid, text=text, geometry=_geo(x, y, w, h, status, polygon),
        provenance=_prov(), lang=lang, confidence=confidence,
        hyphenation=hyphenation,
    )


def _line(lid: str, words: list[Word], x: float = 10, y: float = 10,
          w: float = 200, h: float = 30, lang: str | None = None) -> TextLine:
    return TextLine(
        id=lid, geometry=_geo(x, y, w, h), provenance=_prov(),
        words=words, lang=lang,
    )


def _region(rid: str, lines: list[TextLine], x: float = 0, y: float = 0,
            w: float = 500, h: float = 200, lang: str | None = None) -> TextRegion:
    return TextRegion(
        id=rid, geometry=_geo(x, y, w, h), provenance=_prov(),
        lines=lines, lang=lang,
    )


def _doc(regions: list[TextRegion], width: float = 1000, height: float = 1000,
         reading_order: list[str] | None = None) -> CanonicalDocument:
    return CanonicalDocument(
        document_id="test", source=Source(input_type=InputType.IMAGE),
        pages=[Page(
            id="p1", page_index=0, width=width, height=height,
            text_regions=regions,
            reading_order=reading_order or [],
        )],
    )


# -- PolygonToBbox -----------------------------------------------------------


class TestPolygonToBbox:
    def test_derives_bbox_from_polygon(self) -> None:
        word = _word("w1", "test", status=GeometryStatus.UNKNOWN,
                      polygon=[(100, 200), (400, 200), (400, 250), (100, 250)])
        doc = _doc([_region("tb1", [_line("tl1", [word])])])

        enriched = PolygonToBboxEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.geometry.status == GeometryStatus.INFERRED
        assert w.geometry.bbox == (100, 200, 300, 50)

    def test_skips_when_already_exact(self) -> None:
        word = _word("w1", "test", status=GeometryStatus.EXACT,
                      polygon=[(0, 0), (10, 0), (10, 10), (0, 10)])
        doc = _doc([_region("tb1", [_line("tl1", [word])])])

        enriched = PolygonToBboxEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.geometry.status == GeometryStatus.EXACT

    def test_skips_when_no_polygon(self) -> None:
        word = _word("w1", "test", status=GeometryStatus.UNKNOWN)
        doc = _doc([_region("tb1", [_line("tl1", [word])])])

        enriched = PolygonToBboxEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.geometry.status == GeometryStatus.UNKNOWN

    def test_respects_policy(self) -> None:
        word = _word("w1", "test", status=GeometryStatus.UNKNOWN,
                      polygon=[(0, 0), (10, 0), (10, 10), (0, 10)])
        doc = _doc([_region("tb1", [_line("tl1", [word])])])

        policy = DocumentPolicy(allow_polygon_to_bbox=False)
        enriched = PolygonToBboxEnricher().enrich(doc, policy)
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.geometry.status == GeometryStatus.UNKNOWN


# -- BboxRepairLight ---------------------------------------------------------


class TestBboxRepairLight:
    def test_clips_overflow(self) -> None:
        word = _word("w1", "test", x=950, y=10, w=100, h=30)  # overflows 1000px page
        doc = _doc([_region("tb1", [_line("tl1", [word], x=900, w=200)],
                            x=900, w=200)])

        enriched = BboxRepairLightEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        # Should be clipped to page boundary
        assert w.geometry.bbox[0] + w.geometry.bbox[2] <= 1000
        assert w.geometry.status == GeometryStatus.REPAIRED

    def test_no_change_when_inside(self) -> None:
        word = _word("w1", "test", x=10, y=10, w=50, h=25)
        doc = _doc([_region("tb1", [_line("tl1", [word])])])

        enriched = BboxRepairLightEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.geometry.status == GeometryStatus.EXACT
        assert w.geometry.bbox == (10, 10, 50, 25)


# -- LangPropagation --------------------------------------------------------


class TestLangPropagation:
    def test_propagates_from_region(self) -> None:
        word = _word("w1", "hello", lang=None)
        doc = _doc([_region("tb1", [_line("tl1", [word])], lang="fra")])

        enriched = LangPropagationEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.lang == "fra"

    def test_propagates_from_line(self) -> None:
        word = _word("w1", "hello", lang=None)
        doc = _doc([_region("tb1", [_line("tl1", [word], lang="eng")])])

        enriched = LangPropagationEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.lang == "eng"

    def test_does_not_overwrite_existing(self) -> None:
        word = _word("w1", "hello", lang="deu")
        doc = _doc([_region("tb1", [_line("tl1", [word])], lang="fra")])

        enriched = LangPropagationEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.lang == "deu"

    def test_no_change_when_no_parent_lang(self) -> None:
        word = _word("w1", "hello", lang=None)
        doc = _doc([_region("tb1", [_line("tl1", [word])])])

        enriched = LangPropagationEnricher().enrich(doc, DocumentPolicy())
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.lang is None

    def test_respects_policy(self) -> None:
        word = _word("w1", "hello", lang=None)
        doc = _doc([_region("tb1", [_line("tl1", [word])], lang="fra")])

        policy = DocumentPolicy(allow_lang_propagation=False)
        enriched = LangPropagationEnricher().enrich(doc, policy)
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.lang is None


# -- ReadingOrderSimple ------------------------------------------------------


class TestReadingOrderSimple:
    def test_orders_top_to_bottom(self) -> None:
        r1 = _region("tb_bottom", [_line("tl1", [_word("w1", "b")])], y=200)
        r2 = _region("tb_top", [_line("tl2", [_word("w2", "a")])], y=50)
        doc = _doc([r1, r2], reading_order=[])

        enriched = ReadingOrderSimpleEnricher().enrich(doc, DocumentPolicy())
        assert enriched.pages[0].reading_order == ["tb_top", "tb_bottom"]

    def test_skips_when_order_exists(self) -> None:
        r1 = _region("tb1", [_line("tl1", [_word("w1", "a")])])
        doc = _doc([r1], reading_order=["tb1"])

        enriched = ReadingOrderSimpleEnricher().enrich(doc, DocumentPolicy())
        assert enriched.pages[0].reading_order == ["tb1"]

    def test_respects_policy(self) -> None:
        r1 = _region("tb1", [_line("tl1", [_word("w1", "a")])], y=200)
        r2 = _region("tb2", [_line("tl2", [_word("w2", "b")])], y=50)
        doc = _doc([r1, r2], reading_order=[])

        enriched = ReadingOrderSimpleEnricher().enrich(doc, strict_policy())
        assert enriched.pages[0].reading_order == []


# -- HyphenationBasic -------------------------------------------------------


class TestHyphenationBasic:
    def test_detects_hyphenation(self) -> None:
        line1 = _line("tl1", [_word("w1", "patri-")])
        line2 = _line("tl2", [_word("w2", "moine")], y=50)
        doc = _doc([_region("tb1", [line1, line2])])

        enriched = HyphenationBasicEnricher().enrich(doc, DocumentPolicy())
        lines = enriched.pages[0].text_regions[0].lines
        w1 = lines[0].words[0]
        w2 = lines[1].words[0]

        assert w1.hyphenation is not None
        assert w1.hyphenation.is_hyphenated is True
        assert w1.hyphenation.part == 1
        assert w1.hyphenation.full_form == "patrimoine"

        assert w2.hyphenation is not None
        assert w2.hyphenation.part == 2
        assert w2.hyphenation.full_form == "patrimoine"

    def test_no_hyphenation_without_dash(self) -> None:
        line1 = _line("tl1", [_word("w1", "bonjour")])
        line2 = _line("tl2", [_word("w2", "monde")], y=50)
        doc = _doc([_region("tb1", [line1, line2])])

        enriched = HyphenationBasicEnricher().enrich(doc, DocumentPolicy())
        w1 = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w1.hyphenation is None

    def test_no_hyphenation_if_next_uppercase(self) -> None:
        line1 = _line("tl1", [_word("w1", "anti-")])
        line2 = _line("tl2", [_word("w2", "Américain")], y=50)
        doc = _doc([_region("tb1", [line1, line2])])

        enriched = HyphenationBasicEnricher().enrich(doc, DocumentPolicy())
        w1 = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w1.hyphenation is None

    def test_skips_already_hyphenated(self) -> None:
        hyph = Hyphenation(is_hyphenated=True, part=1, full_form="existing")
        line1 = _line("tl1", [_word("w1", "exist-", hyphenation=hyph)])
        line2 = _line("tl2", [_word("w2", "ing")], y=50)
        doc = _doc([_region("tb1", [line1, line2])])

        enriched = HyphenationBasicEnricher().enrich(doc, DocumentPolicy())
        w1 = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w1.hyphenation.full_form == "existing"  # unchanged

    def test_respects_policy(self) -> None:
        line1 = _line("tl1", [_word("w1", "patri-")])
        line2 = _line("tl2", [_word("w2", "moine")], y=50)
        doc = _doc([_region("tb1", [line1, line2])])

        enriched = HyphenationBasicEnricher().enrich(doc, strict_policy())
        w1 = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w1.hyphenation is None


# -- TextConsistency ---------------------------------------------------------


class TestTextConsistency:
    def test_no_warnings_for_normal_text(self) -> None:
        doc = _doc([_region("tb1", [_line("tl1", [_word("w1", "hello")])])])
        enriched = TextConsistencyEnricher().enrich(doc, DocumentPolicy())
        assert enriched.pages[0].warnings == []

    def test_warns_on_very_long_word(self) -> None:
        long_text = "a" * 150
        doc = _doc([_region("tb1", [_line("tl1", [_word("w1", long_text)])])])
        enriched = TextConsistencyEnricher().enrich(doc, DocumentPolicy())
        assert any("suspiciously long" in w for w in enriched.pages[0].warnings)


# -- Pipeline ----------------------------------------------------------------


class TestEnricherPipeline:
    def test_runs_all_enrichers(self) -> None:
        word = _word("w1", "hello", lang=None)
        doc = _doc([_region("tb1", [_line("tl1", [word])], lang="fra")],
                    reading_order=[])

        pipeline = EnricherPipeline([
            LangPropagationEnricher(),
            ReadingOrderSimpleEnricher(),
            TextConsistencyEnricher(),
        ])
        enriched = pipeline.run(doc)

        # Lang propagated
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.lang == "fra"

        # Reading order inferred
        assert enriched.pages[0].reading_order == ["tb1"]

        # Audit updated
        assert "lang_propagation" in enriched.audit.enrichers_applied
        assert "reading_order_simple" in enriched.audit.enrichers_applied
        assert "text_consistency" in enriched.audit.enrichers_applied

    def test_empty_pipeline_returns_same(self) -> None:
        doc = _doc([_region("tb1", [_line("tl1", [_word("w1", "test")])])])
        pipeline = EnricherPipeline([])
        enriched = pipeline.run(doc)
        assert enriched.document_id == doc.document_id

    def test_respects_policy(self) -> None:
        word = _word("w1", "hello", lang=None)
        doc = _doc([_region("tb1", [_line("tl1", [word])], lang="fra")],
                    reading_order=[])

        pipeline = EnricherPipeline([
            LangPropagationEnricher(),
            ReadingOrderSimpleEnricher(),
        ])
        enriched = pipeline.run(doc, strict_policy())

        # Strict policy blocks both
        w = enriched.pages[0].text_regions[0].lines[0].words[0]
        assert w.lang is None
        assert enriched.pages[0].reading_order == []
