"""Integration test: PaddleOCR → CanonicalDocument → ALTO + PAGE (dual export).

Validates that the same canonical document can be serialized to both
ALTO XML and PAGE XML, and that both outputs are structurally correct.
"""

from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

from src.app.domain.models import RawProviderPayload
from src.app.domain.models.geometry import GeometryContext
from src.app.normalization.pipeline import normalize
from src.app.policies.document_policy import DocumentPolicy
from src.app.policies.export_policy import check_alto_export, check_page_export
from src.app.serializers.alto_xml import ALTO_NS, serialize_alto
from src.app.serializers.page_xml import PAGE_NS, serialize_page_xml
from src.app.validators.export_eligibility_validator import compute_export_eligibility


class TestDualExport:
    """Full pipeline: raw → canon → validate → ALTO + PAGE."""

    def test_both_exports_from_same_document(self, fixtures_dir: Path) -> None:
        # 1. Load and normalize
        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            paddle_output = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr",
            adapter_id="adapter.word_box_json.v1",
            runtime_type="local",
            payload=paddle_output,
            image_width=2480, image_height=3508,
        )
        geo_ctx = GeometryContext(source_width=2480, source_height=3508)

        doc = normalize(
            raw, family="word_box_json", geometry_context=geo_ctx,
            document_id="dual_export_test", source_filename="page.png",
        )

        # 2. Check export eligibility
        policy = DocumentPolicy()
        eligibility = compute_export_eligibility(doc, policy)

        alto_decision = check_alto_export(eligibility, policy)
        page_decision = check_page_export(eligibility, policy)

        assert alto_decision.allowed
        assert page_decision.allowed

        # 3. Serialize both
        alto_bytes = serialize_alto(doc)
        page_bytes = serialize_page_xml(doc)

        assert alto_bytes
        assert page_bytes

        # 4. Parse both
        alto_root = etree.fromstring(alto_bytes)
        page_root = etree.fromstring(page_bytes)

        # 5. Validate ALTO structure
        alto_strings = alto_root.findall(f".//{{{ALTO_NS}}}String")
        assert len(alto_strings) == 5
        assert alto_strings[0].get("CONTENT") == "Bonjour"

        # 6. Validate PAGE structure
        page_words = page_root.findall(f".//{{{PAGE_NS}}}Word")
        assert len(page_words) == 5
        w1_te = page_words[0].find(f".//{{{PAGE_NS}}}Unicode")
        assert w1_te.text == "Bonjour"

        # 7. Verify same word count in both
        assert len(alto_strings) == len(page_words)

        # 8. Verify same text content in both
        alto_texts = [s.get("CONTENT") for s in alto_strings]
        page_texts = [
            w.find(f".//{{{PAGE_NS}}}Unicode").text for w in page_words
        ]
        assert alto_texts == page_texts

    def test_page_has_coords_alto_has_hpos(self, fixtures_dir: Path) -> None:
        """PAGE uses Coords/points, ALTO uses HPOS/VPOS/WIDTH/HEIGHT."""
        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            paddle_output = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr", adapter_id="v1", runtime_type="local",
            payload=paddle_output, image_width=2480, image_height=3508,
        )
        geo_ctx = GeometryContext(source_width=2480, source_height=3508)

        doc = normalize(
            raw, family="word_box_json", geometry_context=geo_ctx,
            document_id="coord_test",
        )

        alto_root = etree.fromstring(serialize_alto(doc))
        page_root = etree.fromstring(serialize_page_xml(doc))

        # ALTO: String has HPOS, VPOS, WIDTH, HEIGHT
        alto_s = alto_root.find(f".//{{{ALTO_NS}}}String")
        assert alto_s.get("HPOS") is not None
        assert alto_s.get("VPOS") is not None
        assert alto_s.get("WIDTH") is not None
        assert alto_s.get("HEIGHT") is not None

        # PAGE: Word has Coords with points
        page_w = page_root.find(f".//{{{PAGE_NS}}}Word")
        coords = page_w.find(f"{{{PAGE_NS}}}Coords")
        assert coords is not None
        points = coords.get("points")
        assert points is not None
        # Points should be polygon (4 vertices from PaddleOCR)
        parts = points.split()
        assert len(parts) == 4

    def test_page_has_reading_order(self, fixtures_dir: Path) -> None:
        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            paddle_output = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr", adapter_id="v1", runtime_type="local",
            payload=paddle_output, image_width=2480, image_height=3508,
        )
        geo_ctx = GeometryContext(source_width=2480, source_height=3508)

        doc = normalize(
            raw, family="word_box_json", geometry_context=geo_ctx,
            document_id="ro_test",
        )

        page_root = etree.fromstring(serialize_page_xml(doc))
        ro = page_root.find(f".//{{{PAGE_NS}}}ReadingOrder")
        assert ro is not None
        refs = ro.findall(f".//{{{PAGE_NS}}}RegionRefIndexed")
        assert len(refs) >= 1
        assert refs[0].get("regionRef") == "tb1"
