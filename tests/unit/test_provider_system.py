"""Tests for the provider system: adapters, registry, resolver."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from src.app.domain.models import GeometryStatus, RawProviderPayload
from src.app.domain.models.geometry import GeometryContext
from src.app.providers.adapters.line_box_json import LineBoxJsonAdapter
from src.app.providers.adapters.text_only import TextOnlyAdapter
from src.app.providers.profiles import ProviderFamily, ProviderProfile, RuntimeType
from src.app.providers.registry import (
    get_adapter,
    get_runtime,
    list_adapter_families,
    list_runtime_types,
)
from src.app.providers.resolver import resolve_provider

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def geo_ctx() -> GeometryContext:
    return GeometryContext(source_width=2480, source_height=3508)


# -- LineBoxJsonAdapter -------------------------------------------------------


class TestLineBoxJsonAdapter:
    @pytest.fixture
    def adapter(self) -> LineBoxJsonAdapter:
        return LineBoxJsonAdapter()

    @pytest.fixture
    def raw(self, fixtures_dir: Path) -> RawProviderPayload:
        with open(fixtures_dir / "line_box_sample.json") as f:
            payload = json.load(f)
        return RawProviderPayload(
            provider_id="line_model", adapter_id="v1", runtime_type="local",
            payload=payload, image_width=2480, image_height=3508,
        )

    def test_family(self, adapter: LineBoxJsonAdapter) -> None:
        assert adapter.family == "line_box_json"

    def test_normalize_produces_document(
        self, adapter: LineBoxJsonAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_line")
        assert doc.document_id == "test_line"
        assert len(doc.pages) == 1

    def test_correct_line_count(
        self, adapter: LineBoxJsonAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test")
        total_lines = sum(
            len(r.lines) for r in doc.pages[0].text_regions
        )
        assert total_lines == 3

    def test_bbox_converted_from_xyxy(
        self, adapter: LineBoxJsonAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test")
        first_line = doc.pages[0].text_regions[0].lines[0]
        x, y, w, h = first_line.geometry.bbox
        # From fixture: [100, 200, 600, 240] → xyxy → xywh: (100, 200, 500, 40)
        assert x == pytest.approx(100)
        assert y == pytest.approx(200)
        assert w == pytest.approx(500)
        assert h == pytest.approx(40)

    def test_text_preserved(
        self, adapter: LineBoxJsonAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test")
        word = doc.pages[0].text_regions[0].lines[0].words[0]
        assert word.text == "Bonjour le monde"

    def test_geometry_status_exact(
        self, adapter: LineBoxJsonAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test")
        line = doc.pages[0].text_regions[0].lines[0]
        assert line.geometry.status == GeometryStatus.EXACT

    def test_empty_payload_rejected(
        self, adapter: LineBoxJsonAdapter, geo_ctx: GeometryContext,
    ) -> None:
        raw = RawProviderPayload(
            provider_id="t", adapter_id="v1", runtime_type="local", payload=[],
        )
        with pytest.raises(ValueError, match="no items"):
            adapter.normalize(raw, geo_ctx, document_id="test")

    def test_dict_payload_rejected(
        self, adapter: LineBoxJsonAdapter, geo_ctx: GeometryContext,
    ) -> None:
        raw = RawProviderPayload(
            provider_id="t", adapter_id="v1", runtime_type="local",
            payload={"not": "a list"},
        )
        with pytest.raises(ValueError, match="list payload"):
            adapter.normalize(raw, geo_ctx, document_id="test")


# -- TextOnlyAdapter ----------------------------------------------------------


class TestTextOnlyAdapter:
    @pytest.fixture
    def adapter(self) -> TextOnlyAdapter:
        return TextOnlyAdapter()

    @pytest.fixture
    def raw(self, fixtures_dir: Path) -> RawProviderPayload:
        with open(fixtures_dir / "text_only_sample.json") as f:
            payload = json.load(f)
        return RawProviderPayload(
            provider_id="qwen3_vl", adapter_id="v1", runtime_type="api",
            payload=payload, image_width=2480, image_height=3508,
        )

    def test_family(self, adapter: TextOnlyAdapter) -> None:
        assert adapter.family == "text_only"

    def test_normalize_produces_document(
        self, adapter: TextOnlyAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test_text")
        assert doc.document_id == "test_text"
        assert len(doc.pages) == 1

    def test_splits_paragraphs(
        self, adapter: TextOnlyAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test")
        # Fixture has 2 paragraphs separated by \n\n
        assert len(doc.pages[0].text_regions) == 2

    def test_geometry_is_unknown(
        self, adapter: TextOnlyAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test")
        word = doc.pages[0].text_regions[0].lines[0].words[0]
        assert word.geometry.status == GeometryStatus.UNKNOWN

    def test_text_preserved(
        self, adapter: TextOnlyAdapter, raw: RawProviderPayload, geo_ctx: GeometryContext,
    ) -> None:
        doc = adapter.normalize(raw, geo_ctx, document_id="test")
        first_word = doc.pages[0].text_regions[0].lines[0].words[0]
        assert "Bonjour" in first_word.text

    def test_no_text_rejected(
        self, adapter: TextOnlyAdapter, geo_ctx: GeometryContext,
    ) -> None:
        raw = RawProviderPayload(
            provider_id="t", adapter_id="v1", runtime_type="api",
            payload={"text": ""},
        )
        with pytest.raises(ValueError, match="no text"):
            adapter.normalize(raw, geo_ctx, document_id="test")

    def test_list_payload_rejected(
        self, adapter: TextOnlyAdapter, geo_ctx: GeometryContext,
    ) -> None:
        raw = RawProviderPayload(
            provider_id="t", adapter_id="v1", runtime_type="api",
            payload=[1, 2, 3],
        )
        with pytest.raises(ValueError, match="dict payload"):
            adapter.normalize(raw, geo_ctx, document_id="test")

    def test_with_blocks(
        self, adapter: TextOnlyAdapter, geo_ctx: GeometryContext,
    ) -> None:
        raw = RawProviderPayload(
            provider_id="t", adapter_id="v1", runtime_type="api",
            payload={
                "text": "ignored",
                "blocks": [
                    {"text": "Block one line one\nBlock one line two"},
                    {"text": "Block two"},
                ],
            },
        )
        doc = adapter.normalize(raw, geo_ctx, document_id="test")
        assert len(doc.pages[0].text_regions) == 2
        assert len(doc.pages[0].text_regions[0].lines) == 2


# -- Registry -----------------------------------------------------------------


class TestRegistry:
    def test_list_families(self) -> None:
        families = list_adapter_families()
        assert "word_box_json" in families
        assert "line_box_json" in families
        assert "text_only" in families

    def test_list_runtimes(self) -> None:
        types = list_runtime_types()
        assert "local" in types
        assert "hub" in types
        assert "api" in types

    def test_get_adapter_word_box(self) -> None:
        adapter = get_adapter("word_box_json")
        assert adapter.family == "word_box_json"

    def test_get_adapter_line_box(self) -> None:
        adapter = get_adapter("line_box_json")
        assert adapter.family == "line_box_json"

    def test_get_adapter_text_only(self) -> None:
        adapter = get_adapter("text_only")
        assert adapter.family == "text_only"

    def test_get_adapter_unknown(self) -> None:
        with pytest.raises(KeyError, match="No adapter"):
            get_adapter("unknown_family")

    def test_get_runtime_local(self) -> None:
        rt = get_runtime("local")
        assert rt.is_available()

    def test_get_runtime_api(self) -> None:
        rt = get_runtime("api")
        assert rt.is_available()

    def test_get_runtime_hub(self) -> None:
        rt = get_runtime("hub")
        # is_available depends on whether huggingface_hub is installed
        assert isinstance(rt.is_available(), bool)

    def test_hub_runtime_execute_raises(self) -> None:
        rt = get_runtime("hub")
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            from pathlib import Path
            rt.execute(Path("/fake.png"), "model_id")

    def test_local_runtime_execute_raises(self) -> None:
        rt = get_runtime("local")
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            from pathlib import Path
            rt.execute(Path("/fake.png"), "model_id")

    def test_api_runtime_execute_raises(self) -> None:
        rt = get_runtime("api")
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            from pathlib import Path
            rt.execute(Path("/fake.png"), "model_id")

    def test_get_runtime_unknown(self) -> None:
        with pytest.raises(KeyError, match="No runtime"):
            get_runtime("unknown_type")


# -- Resolver -----------------------------------------------------------------


class TestResolver:
    def test_resolve_word_box_local(self) -> None:
        profile = ProviderProfile(
            provider_id="paddle_test",
            display_name="PaddleOCR Test",
            runtime_type=RuntimeType.LOCAL,
            model_id_or_path="/models/paddle",
            family=ProviderFamily.WORD_BOX_JSON,
        )
        resolved = resolve_provider(profile)
        assert resolved.provider_id == "paddle_test"
        assert resolved.family == "word_box_json"
        assert resolved.adapter.family == "word_box_json"

    def test_resolve_text_only_api(self) -> None:
        profile = ProviderProfile(
            provider_id="qwen_test",
            display_name="Qwen Test",
            runtime_type=RuntimeType.API,
            model_id_or_path="qwen3-vl",
            family=ProviderFamily.TEXT_ONLY,
            endpoint="https://api.example.com/v1",
        )
        resolved = resolve_provider(profile)
        assert resolved.family == "text_only"
        assert resolved.runtime.is_available()

    def test_resolve_line_box_hub(self) -> None:
        profile = ProviderProfile(
            provider_id="hub_test",
            display_name="Hub Model",
            runtime_type=RuntimeType.HUB,
            model_id_or_path="user/model",
            family=ProviderFamily.LINE_BOX_JSON,
        )
        resolved = resolve_provider(profile)
        assert resolved.family == "line_box_json"
