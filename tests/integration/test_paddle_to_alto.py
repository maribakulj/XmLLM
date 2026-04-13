"""Integration test: PaddleOCR raw output → CanonicalDocument → ALTO XML.

This is the Sprint 3 vertical slice end-to-end test.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from lxml import etree
from src.app.domain.models import RawProviderPayload
from src.app.domain.models.geometry import GeometryContext
from src.app.normalization.pipeline import normalize
from src.app.serializers.alto_xml import ALTO_NS, serialize_alto

if TYPE_CHECKING:
    from pathlib import Path


class TestPaddleToAlto:
    """Full pipeline: raw fixture → normalize → serialize → valid ALTO."""

    def test_end_to_end(self, fixtures_dir: Path) -> None:
        # 1. Load raw PaddleOCR output
        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            paddle_output = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr",
            adapter_id="adapter.word_box_json.v1",
            runtime_type="local",
            payload=paddle_output,
            image_width=2480,
            image_height=3508,
        )

        geo_ctx = GeometryContext(source_width=2480, source_height=3508)

        # 2. Normalize to CanonicalDocument
        doc = normalize(
            raw,
            family="word_box_json",
            geometry_context=geo_ctx,
            document_id="integration_test_001",
            source_filename="page_001.png",
        )

        # Verify canonical document structure
        assert doc.document_id == "integration_test_001"
        assert doc.source.filename == "page_001.png"
        assert len(doc.pages) == 1

        page = doc.pages[0]
        assert page.width == 2480
        assert page.height == 3508
        assert len(page.text_regions) >= 1

        # Count total words
        all_words = [
            w
            for r in page.text_regions
            for ln in r.lines
            for w in ln.words
        ]
        assert len(all_words) == 5

        # Verify provenance chain
        for word in all_words:
            assert word.provenance.provider == "paddleocr"
            assert word.geometry.polygon is not None

        # 3. Serialize to ALTO XML
        alto_bytes = serialize_alto(doc)
        assert alto_bytes  # not empty

        # 4. Parse and validate ALTO structure
        root = etree.fromstring(alto_bytes)
        assert root.tag == f"{{{ALTO_NS}}}alto"

        # Verify page
        alto_page = root.find(f".//{{{ALTO_NS}}}Page")
        assert alto_page is not None
        assert alto_page.get("WIDTH") == "2480"
        assert alto_page.get("HEIGHT") == "3508"

        # Verify strings
        strings = root.findall(f".//{{{ALTO_NS}}}String")
        assert len(strings) == 5

        # First word content matches
        assert strings[0].get("CONTENT") == "Bonjour"

        # Coordinates are integers
        for s in strings:
            assert s.get("HPOS").isdigit()
            assert s.get("VPOS").isdigit()
            assert s.get("WIDTH").isdigit()
            assert s.get("HEIGHT").isdigit()

        # Confidence present
        assert strings[0].get("WC") == "0.96"

        # SP elements between words within a line
        text_lines = root.findall(f".//{{{ALTO_NS}}}TextLine")
        assert len(text_lines) == 5  # each paddle item = 1 line

    def test_canonical_json_roundtrip(self, fixtures_dir: Path) -> None:
        """The canonical doc produced by the pipeline survives JSON serialization."""
        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            paddle_output = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr",
            adapter_id="v1",
            runtime_type="local",
            payload=paddle_output,
            image_width=2480,
            image_height=3508,
        )

        geo_ctx = GeometryContext(source_width=2480, source_height=3508)
        doc = normalize(
            raw,
            family="word_box_json",
            geometry_context=geo_ctx,
            document_id="roundtrip_test",
        )

        # Serialize to JSON and back
        json_str = doc.model_dump_json()
        from src.app.domain.models import CanonicalDocument

        doc2 = CanonicalDocument.model_validate_json(json_str)

        # Same structure
        assert doc2.document_id == doc.document_id
        assert len(doc2.pages) == 1
        words_original = [
            w.text for r in doc.pages[0].text_regions for ln in r.lines for w in ln.words
        ]
        words_restored = [
            w.text for r in doc2.pages[0].text_regions for ln in r.lines for w in ln.words
        ]
        assert words_original == words_restored

        # Same ALTO output
        alto1 = serialize_alto(doc)
        alto2 = serialize_alto(doc2)
        assert alto1 == alto2
