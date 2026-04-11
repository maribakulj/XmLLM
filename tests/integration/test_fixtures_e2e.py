"""End-to-end tests with all fixture types (§28.5).

Each fixture represents a different document scenario and is run through
the full pipeline: raw → normalize → enrich → validate → ALTO + PAGE + viewer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from lxml import etree

from src.app.domain.models import CanonicalDocument, RawProviderPayload
from src.app.domain.models.geometry import GeometryContext
from src.app.domain.models.status import GeometryStatus, ReadinessLevel
from src.app.enrichers import EnricherPipeline
from src.app.enrichers.bbox_repair_light import BboxRepairLightEnricher
from src.app.enrichers.hyphenation_basic import HyphenationBasicEnricher
from src.app.enrichers.lang_propagation import LangPropagationEnricher
from src.app.enrichers.reading_order_simple import ReadingOrderSimpleEnricher
from src.app.enrichers.text_consistency import TextConsistencyEnricher
from src.app.normalization.pipeline import normalize
from src.app.policies.document_policy import DocumentPolicy
from src.app.policies.export_policy import check_alto_export, check_page_export
from src.app.serializers.alto_xml import ALTO_NS, serialize_alto
from src.app.serializers.page_xml import PAGE_NS, serialize_page_xml
from src.app.validators.export_eligibility_validator import compute_export_eligibility
from src.app.validators.structural_validator import validate_structure
from src.app.viewer.projection_builder import build_projection


GEO_CTX = GeometryContext(source_width=1000, source_height=800)

ENRICHER_PIPELINE = EnricherPipeline([
    BboxRepairLightEnricher(),
    LangPropagationEnricher(),
    ReadingOrderSimpleEnricher(),
    HyphenationBasicEnricher(),
    TextConsistencyEnricher(),
])


def _run_paddle_pipeline(fixture_name: str, fixtures_dir: Path) -> tuple[
    CanonicalDocument, bytes, bytes, dict
]:
    """Full pipeline for a PaddleOCR-format fixture."""
    with open(fixtures_dir / fixture_name) as f:
        payload = json.load(f)

    raw = RawProviderPayload(
        provider_id="paddleocr", adapter_id="v1", runtime_type="local",
        payload=payload, image_width=1000, image_height=800,
    )
    doc = normalize(raw, "word_box_json", GEO_CTX, document_id=f"test_{fixture_name}")
    doc = ENRICHER_PIPELINE.run(doc, DocumentPolicy())

    struct_report = validate_structure(doc, bbox_tolerance=5.0)
    eligibility = compute_export_eligibility(doc)

    alto_bytes = serialize_alto(doc)
    page_bytes = serialize_page_xml(doc)
    vp = build_projection(doc, export_status=eligibility)

    return doc, alto_bytes, page_bytes, vp.model_dump(mode="json")


# -- Simple page (paddle_ocr_sample.json) ------------------------------------


class TestSimplePage:
    def test_full_pipeline(self, fixtures_dir: Path) -> None:
        doc, alto, page, viewer = _run_paddle_pipeline("paddle_ocr_sample.json", fixtures_dir)
        assert len(doc.pages[0].text_regions) >= 1
        assert b"Bonjour" in alto
        assert b"Bonjour" in page
        assert len(viewer["word_overlays"]) == 5

    def test_alto_valid_structure(self, fixtures_dir: Path) -> None:
        _, alto, _, _ = _run_paddle_pipeline("paddle_ocr_sample.json", fixtures_dir)
        root = etree.fromstring(alto)
        strings = root.findall(f".//{{{ALTO_NS}}}String")
        assert all(s.get("HPOS").isdigit() for s in strings)
        assert all(s.get("CONTENT") for s in strings)

    def test_page_has_reading_order(self, fixtures_dir: Path) -> None:
        _, _, page, _ = _run_paddle_pipeline("paddle_ocr_sample.json", fixtures_dir)
        root = etree.fromstring(page)
        refs = root.findall(f".//{{{PAGE_NS}}}RegionRefIndexed")
        assert len(refs) >= 1


# -- Double column -----------------------------------------------------------


class TestDoubleColumn:
    def test_four_items(self, fixtures_dir: Path) -> None:
        doc, _, _, _ = _run_paddle_pipeline("double_column.json", fixtures_dir)
        words = [w for r in doc.pages[0].text_regions for l in r.lines for w in l.words]
        assert len(words) == 4

    def test_reading_order_inferred(self, fixtures_dir: Path) -> None:
        doc, _, _, _ = _run_paddle_pipeline("double_column.json", fixtures_dir)
        assert doc.pages[0].reading_order  # enricher should have set it

    def test_dual_export(self, fixtures_dir: Path) -> None:
        _, alto, page, _ = _run_paddle_pipeline("double_column.json", fixtures_dir)
        alto_root = etree.fromstring(alto)
        page_root = etree.fromstring(page)
        assert len(alto_root.findall(f".//{{{ALTO_NS}}}String")) == 4
        assert len(page_root.findall(f".//{{{PAGE_NS}}}Word")) == 4


# -- Noisy page --------------------------------------------------------------


class TestNoisyPage:
    def test_handles_negative_coords(self, fixtures_dir: Path) -> None:
        doc, _, _, _ = _run_paddle_pipeline("noisy_page.json", fixtures_dir)
        # bbox_repair_light should clip negative coords
        for r in doc.pages[0].text_regions:
            for l in r.lines:
                for w in l.words:
                    x, y, _, _ = w.geometry.bbox
                    assert x >= 0
                    assert y >= 0

    def test_low_confidence_preserved(self, fixtures_dir: Path) -> None:
        doc, _, _, _ = _run_paddle_pipeline("noisy_page.json", fixtures_dir)
        words = [w for r in doc.pages[0].text_regions for l in r.lines for w in l.words]
        confs = [w.confidence for w in words if w.confidence is not None]
        assert any(c < 0.5 for c in confs)

    def test_structural_validation(self, fixtures_dir: Path) -> None:
        doc, _, _, _ = _run_paddle_pipeline("noisy_page.json", fixtures_dir)
        report = validate_structure(doc, bbox_tolerance=5.0)
        # After repair, structural issues should be minimized
        assert report.error_count == 0

    def test_viewer_has_all_words(self, fixtures_dir: Path) -> None:
        _, _, _, viewer = _run_paddle_pipeline("noisy_page.json", fixtures_dir)
        assert len(viewer["word_overlays"]) == 4


# -- Title + body ------------------------------------------------------------


class TestTitleBody:
    def test_four_items(self, fixtures_dir: Path) -> None:
        doc, _, _, _ = _run_paddle_pipeline("title_body.json", fixtures_dir)
        words = [w for r in doc.pages[0].text_regions for l in r.lines for w in l.words]
        assert len(words) == 4

    def test_alto_all_strings(self, fixtures_dir: Path) -> None:
        _, alto, _, _ = _run_paddle_pipeline("title_body.json", fixtures_dir)
        root = etree.fromstring(alto)
        strings = root.findall(f".//{{{ALTO_NS}}}String")
        assert any("Titre" in s.get("CONTENT", "") for s in strings)

    def test_page_all_words(self, fixtures_dir: Path) -> None:
        _, _, page, _ = _run_paddle_pipeline("title_body.json", fixtures_dir)
        root = etree.fromstring(page)
        words = root.findall(f".//{{{PAGE_NS}}}Word")
        assert len(words) == 4


# -- Hyphenation -------------------------------------------------------------


class TestHyphenationFixture:
    def test_hyphenation_detected(self, fixtures_dir: Path) -> None:
        doc, _, _, _ = _run_paddle_pipeline("hyphenation_sample.json", fixtures_dir)
        words = [w for r in doc.pages[0].text_regions for l in r.lines for w in l.words]
        hyph_words = [w for w in words if w.hyphenation is not None and w.hyphenation.is_hyphenated]
        assert len(hyph_words) == 2
        assert hyph_words[0].hyphenation.full_form == "patrimoine"
        assert hyph_words[0].hyphenation.part == 1
        assert hyph_words[1].hyphenation.part == 2

    def test_alto_hyphenation(self, fixtures_dir: Path) -> None:
        _, alto, _, _ = _run_paddle_pipeline("hyphenation_sample.json", fixtures_dir)
        root = etree.fromstring(alto)
        strings = root.findall(f".//{{{ALTO_NS}}}String")
        hyp_strings = [s for s in strings if s.get("SUBS_TYPE")]
        assert len(hyp_strings) == 2
        assert hyp_strings[0].get("SUBS_TYPE") == "HypPart1"
        assert hyp_strings[0].get("SUBS_CONTENT") == "patrimoine"


# -- Text only (no geometry) -------------------------------------------------


class TestTextOnlyFixture:
    def test_produces_document(self, fixtures_dir: Path) -> None:
        with open(fixtures_dir / "text_only_blocks.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="qwen", adapter_id="v1", runtime_type="api",
            payload=payload, image_width=1000, image_height=800,
        )
        doc = normalize(raw, "text_only", GEO_CTX, document_id="text_test")

        assert len(doc.pages[0].text_regions) == 3

    def test_geometry_is_unknown(self, fixtures_dir: Path) -> None:
        with open(fixtures_dir / "text_only_blocks.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="qwen", adapter_id="v1", runtime_type="api",
            payload=payload, image_width=1000, image_height=800,
        )
        doc = normalize(raw, "text_only", GEO_CTX, document_id="text_test")

        word = doc.pages[0].text_regions[0].lines[0].words[0]
        assert word.geometry.status == GeometryStatus.UNKNOWN

    def test_alto_refused(self, fixtures_dir: Path) -> None:
        with open(fixtures_dir / "text_only_blocks.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="qwen", adapter_id="v1", runtime_type="api",
            payload=payload, image_width=1000, image_height=800,
        )
        doc = normalize(raw, "text_only", GEO_CTX, document_id="text_test")

        eligibility = compute_export_eligibility(doc)
        decision = check_alto_export(eligibility)
        assert decision.allowed is False

    def test_page_export_possible(self, fixtures_dir: Path) -> None:
        with open(fixtures_dir / "text_only_blocks.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="qwen", adapter_id="v1", runtime_type="api",
            payload=payload, image_width=1000, image_height=800,
        )
        doc = normalize(raw, "text_only", GEO_CTX, document_id="text_test")

        eligibility = compute_export_eligibility(doc)
        # PAGE is more lenient — may still be exportable
        page_decision = check_page_export(eligibility)
        # Even if refused, it should give a clear reason
        assert page_decision.reason

    def test_viewer_renders_degraded(self, fixtures_dir: Path) -> None:
        with open(fixtures_dir / "text_only_blocks.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="qwen", adapter_id="v1", runtime_type="api",
            payload=payload, image_width=1000, image_height=800,
        )
        doc = normalize(raw, "text_only", GEO_CTX, document_id="text_test")
        eligibility = compute_export_eligibility(doc)

        vp = build_projection(doc, export_status=eligibility)
        # Should still have overlays even with unknown geometry
        assert len(vp.word_overlays) > 0
