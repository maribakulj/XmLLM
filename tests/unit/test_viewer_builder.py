"""Tests for the ViewerProjection builder and overlay generation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from src.app.domain.models import (
    AltoReadiness,
    CanonicalDocument,
    EvidenceType,
    ExportEligibility,
    Geometry,
    GeometryStatus,
    NonTextRegion,
    OverlayLevel,
    Page,
    PageXmlReadiness,
    Provenance,
    RawProviderPayload,
    ReadinessLevel,
    Source,
    TextLine,
    TextRegion,
    Word,
)
from src.app.domain.models.geometry import GeometryContext
from src.app.domain.models.status import BlockRole, InputType, NonTextKind
from src.app.normalization.pipeline import normalize
from src.app.viewer.overlays import (
    line_to_overlay,
    region_to_overlay,
    word_to_inspection,
    word_to_overlay,
)
from src.app.viewer.projection_builder import build_all_projections, build_projection

if TYPE_CHECKING:
    from pathlib import Path


def _prov() -> Provenance:
    return Provenance(
        provider="test", adapter="v1", source_ref="$",
        evidence_type=EvidenceType.PROVIDER_NATIVE,
    )


def _geo(x: float = 10, y: float = 10, w: float = 100, h: float = 30) -> Geometry:
    return Geometry(bbox=(x, y, w, h), status=GeometryStatus.EXACT)


def _simple_doc() -> CanonicalDocument:
    return CanonicalDocument(
        document_id="viewer_test",
        source=Source(input_type=InputType.IMAGE, filename="test.png"),
        pages=[Page(
            id="p1", page_index=0, width=2480, height=3508,
            alto_readiness=AltoReadiness(level=ReadinessLevel.FULL),
            page_readiness=PageXmlReadiness(level=ReadinessLevel.FULL),
            reading_order=["tb1"],
            text_regions=[TextRegion(
                id="tb1", role=BlockRole.BODY,
                geometry=_geo(100, 200, 1200, 900), provenance=_prov(), lang="fra",
                lines=[
                    TextLine(id="tl1", geometry=_geo(110, 220, 1100, 42),
                             provenance=_prov(), lang="fra",
                             words=[
                                 Word(id="w1", text="Bonjour", geometry=_geo(110, 220, 90, 40),
                                      provenance=_prov(), confidence=0.96, lang="fra"),
                                 Word(id="w2", text="monde", geometry=_geo(220, 220, 80, 40),
                                      provenance=_prov(), confidence=0.94, lang="fra"),
                             ]),
                    TextLine(id="tl2", geometry=_geo(110, 280, 1100, 42),
                             provenance=_prov(),
                             words=[
                                 Word(id="w3", text="Test", geometry=_geo(110, 280, 60, 40),
                                      provenance=_prov(), confidence=0.90),
                             ]),
                ],
            )],
            non_text_regions=[NonTextRegion(
                id="ntr1", kind=NonTextKind.ILLUSTRATION,
                geometry=_geo(1500, 200, 400, 300), provenance=_prov(),
            )],
        )],
    )


# -- Overlay unit tests -------------------------------------------------------


class TestOverlayGeneration:
    def test_word_overlay(self) -> None:
        w = Word(id="w1", text="Hello", geometry=_geo(10, 20, 50, 30),
                 provenance=_prov(), confidence=0.95, lang="eng")
        ov = word_to_overlay(w)
        assert ov.id == "w1"
        assert ov.level == OverlayLevel.WORD
        assert ov.text == "Hello"
        assert ov.bbox == (10, 20, 50, 30)
        assert ov.confidence == 0.95
        assert ov.provenance_type == EvidenceType.PROVIDER_NATIVE
        assert ov.geometry_status == GeometryStatus.EXACT

    def test_line_overlay(self) -> None:
        line = TextLine(id="tl1", geometry=_geo(10, 20, 200, 30),
                        provenance=_prov(),
                        words=[Word(id="w1", text="Hello", geometry=_geo(),
                                    provenance=_prov())])
        ov = line_to_overlay(line)
        assert ov.id == "tl1"
        assert ov.level == OverlayLevel.LINE
        assert ov.text == "Hello"

    def test_region_overlay(self) -> None:
        r = TextRegion(id="tb1", role=BlockRole.HEADING,
                       geometry=_geo(0, 0, 500, 100), provenance=_prov(),
                       lines=[TextLine(id="tl1", geometry=_geo(),
                                       provenance=_prov(),
                                       words=[Word(id="w1", text="Title",
                                                   geometry=_geo(),
                                                   provenance=_prov())])])
        ov = region_to_overlay(r)
        assert ov.id == "tb1"
        assert ov.level == OverlayLevel.BLOCK
        assert ov.label == "heading"

    def test_word_inspection(self) -> None:
        w = Word(id="w1", text="Hello", geometry=_geo(10, 20, 50, 30),
                 provenance=_prov(), confidence=0.95, lang="eng")
        insp = word_to_inspection(w)
        assert insp.id == "w1"
        assert insp.text == "Hello"
        assert insp.lang == "eng"
        assert insp.provenance_provider == "test"


# -- Projection builder -------------------------------------------------------


class TestProjectionBuilder:
    def test_build_projection(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        assert vp.image_ref == "test.png"
        assert vp.image_width == 2480
        assert vp.image_height == 3508

    def test_block_overlays(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        assert len(vp.block_overlays) == 1
        assert vp.block_overlays[0].id == "tb1"

    def test_line_overlays(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        assert len(vp.line_overlays) == 2

    def test_word_overlays(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        assert len(vp.word_overlays) == 3
        word_ids = {o.id for o in vp.word_overlays}
        assert word_ids == {"w1", "w2", "w3"}

    def test_non_text_overlays(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        assert len(vp.non_text_overlays) == 1
        assert vp.non_text_overlays[0].id == "ntr1"

    def test_inspection_index(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        # Should contain all blocks, lines, and words
        assert "tb1" in vp.inspection_index
        assert "tl1" in vp.inspection_index
        assert "tl2" in vp.inspection_index
        assert "w1" in vp.inspection_index
        assert "w2" in vp.inspection_index
        assert "w3" in vp.inspection_index

    def test_inspection_data_content(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        w1 = vp.inspection_index["w1"]
        assert w1.text == "Bonjour"
        assert w1.confidence == 0.96
        assert w1.lang == "fra"
        assert w1.provenance_provider == "test"

    def test_export_status_default(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        assert vp.export_status.alto_export == ReadinessLevel.NONE

    def test_export_status_custom(self) -> None:
        doc = _simple_doc()
        elig = ExportEligibility(
            alto_export=ReadinessLevel.FULL,
            page_export=ReadinessLevel.FULL,
            viewer_render=ReadinessLevel.FULL,
        )
        vp = build_projection(doc, export_status=elig)
        assert vp.export_status.alto_export == ReadinessLevel.FULL

    def test_page_index_out_of_range(self) -> None:
        doc = _simple_doc()
        with pytest.raises(ValueError, match="out of range"):
            build_projection(doc, page_index=5)

    def test_build_all_projections(self) -> None:
        doc = _simple_doc()
        projections = build_all_projections(doc)
        assert len(projections) == 1
        assert projections[0].image_width == 2480

    def test_json_roundtrip(self) -> None:
        doc = _simple_doc()
        vp = build_projection(doc)
        data = vp.model_dump(mode="json")
        # Verify it's fully serializable
        import json
        json_str = json.dumps(data)
        restored = json.loads(json_str)
        assert restored["image_width"] == 2480
        assert len(restored["word_overlays"]) == 3
        assert "w1" in restored["inspection_index"]


class TestProjectionFromPipeline:
    """Integration: PaddleOCR raw → normalize → build_projection."""

    def test_from_paddle(self, fixtures_dir: Path) -> None:
        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr", adapter_id="v1", runtime_type="local",
            payload=payload, image_width=2480, image_height=3508,
        )
        geo_ctx = GeometryContext(source_width=2480, source_height=3508)

        doc = normalize(raw, family="word_box_json", geometry_context=geo_ctx,
                        document_id="vp_test", source_filename="page.png")

        vp = build_projection(doc)
        assert vp.image_ref == "page.png"
        assert len(vp.word_overlays) == 5
        assert vp.word_overlays[0].text == "Bonjour"
        assert len(vp.inspection_index) > 0
