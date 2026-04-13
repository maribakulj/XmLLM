"""Tests for the word_box_json adapter (PaddleOCR format)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from src.app.domain.models import (
    EvidenceType,
    GeometryStatus,
    RawProviderPayload,
)
from src.app.domain.models.geometry import GeometryContext
from src.app.providers.adapters.word_box_json import WordBoxJsonAdapter

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def adapter() -> WordBoxJsonAdapter:
    return WordBoxJsonAdapter()


@pytest.fixture
def paddle_payload(fixtures_dir: Path) -> list:
    with open(fixtures_dir / "paddle_ocr_sample.json") as f:
        return json.load(f)


@pytest.fixture
def raw(paddle_payload: list) -> RawProviderPayload:
    return RawProviderPayload(
        provider_id="paddleocr",
        adapter_id="adapter.word_box_json.v1",
        runtime_type="local",
        payload=paddle_payload,
        image_width=2480,
        image_height=3508,
    )


@pytest.fixture
def geo_ctx() -> GeometryContext:
    return GeometryContext(source_width=2480, source_height=3508)


class TestWordBoxJsonAdapter:
    def test_family(self, adapter: WordBoxJsonAdapter) -> None:
        assert adapter.family == "word_box_json"

    def test_version(self, adapter: WordBoxJsonAdapter) -> None:
        assert "v1" in adapter.version

    def test_normalize_produces_valid_document(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(
            raw, geo_ctx, document_id="test_doc", source_filename="test.png"
        )
        assert doc.document_id == "test_doc"
        assert doc.source.filename == "test.png"
        assert len(doc.pages) == 1

    def test_page_dimensions(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        page = doc.pages[0]
        assert page.width == 2480
        assert page.height == 3508

    def test_correct_word_count(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        page = doc.pages[0]
        # 5 items in fixture → 5 lines, each with 1 word
        total_words = sum(
            len(line.words)
            for region in page.text_regions
            for line in region.lines
        )
        assert total_words == 5

    def test_word_text_preserved(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        words = [
            w.text
            for r in doc.pages[0].text_regions
            for ln in r.lines
            for w in ln.words
        ]
        assert words[0] == "Bonjour"
        assert words[1] == "le"
        assert words[2] == "monde"

    def test_confidence_preserved(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        first_word = doc.pages[0].text_regions[0].lines[0].words[0]
        assert first_word.confidence == pytest.approx(0.96)

    def test_geometry_is_exact(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        first_word = doc.pages[0].text_regions[0].lines[0].words[0]
        assert first_word.geometry.status == GeometryStatus.EXACT

    def test_polygon_preserved(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        first_word = doc.pages[0].text_regions[0].lines[0].words[0]
        assert first_word.geometry.polygon is not None
        assert len(first_word.geometry.polygon) == 4

    def test_bbox_correct(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        first_word = doc.pages[0].text_regions[0].lines[0].words[0]
        # From fixture: [[100,200],[300,200],[300,240],[100,240]]
        # → bbox = (100, 200, 200, 40)
        x, y, w, h = first_word.geometry.bbox
        assert x == pytest.approx(100)
        assert y == pytest.approx(200)
        assert w == pytest.approx(200)
        assert h == pytest.approx(40)

    def test_provenance_native(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        first_word = doc.pages[0].text_regions[0].lines[0].words[0]
        assert first_word.provenance.evidence_type == EvidenceType.PROVIDER_NATIVE
        assert first_word.provenance.provider == "paddleocr"
        assert "$[0]" in first_word.provenance.source_ref

    def test_block_is_inferred(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        region = doc.pages[0].text_regions[0]
        assert region.geometry.status == GeometryStatus.INFERRED
        assert region.provenance.evidence_type == EvidenceType.DERIVED

    def test_reading_order(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        assert doc.pages[0].reading_order == ["tb1"]

    def test_empty_payload_rejected(
        self,
        adapter: WordBoxJsonAdapter,
        geo_ctx: GeometryContext,
    ) -> None:
        raw = RawProviderPayload(
            provider_id="test",
            adapter_id="v1",
            runtime_type="local",
            payload=[],
        )
        with pytest.raises(ValueError, match="no items"):
            adapter.normalize(raw, geo_ctx, document_id="test_doc")

    def test_dict_payload_rejected(
        self,
        adapter: WordBoxJsonAdapter,
        geo_ctx: GeometryContext,
    ) -> None:
        raw = RawProviderPayload(
            provider_id="test",
            adapter_id="v1",
            runtime_type="local",
            payload={"not": "a list"},
        )
        with pytest.raises(ValueError, match="list payload"):
            adapter.normalize(raw, geo_ctx, document_id="test_doc")

    def test_json_roundtrip(
        self,
        adapter: WordBoxJsonAdapter,
        raw: RawProviderPayload,
        geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_doc")
        data = doc.model_dump(mode="json")
        from src.app.domain.models import CanonicalDocument

        doc2 = CanonicalDocument.model_validate(data)
        assert doc2.document_id == doc.document_id
