"""Tests for the ViewerProjection model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.app.domain.models import (
    EvidenceType,
    ExportEligibility,
    GeometryStatus,
    OverlayLevel,
    ReadinessLevel,
)
from src.app.domain.models.viewer_projection import (
    InspectionData,
    OverlayItem,
    ViewerProjection,
)


class TestOverlayItem:
    def test_valid_word_overlay(self) -> None:
        o = OverlayItem(
            id="w1",
            level=OverlayLevel.WORD,
            bbox=(110, 220, 90, 40),
            text="Bonjour",
            confidence=0.96,
            provenance_type=EvidenceType.PROVIDER_NATIVE,
            geometry_status=GeometryStatus.EXACT,
        )
        assert o.level == OverlayLevel.WORD
        assert o.text == "Bonjour"

    def test_valid_block_overlay(self) -> None:
        o = OverlayItem(
            id="tb1",
            level=OverlayLevel.BLOCK,
            bbox=(100, 200, 1200, 900),
            label="body",
        )
        assert o.level == OverlayLevel.BLOCK

    def test_with_polygon(self) -> None:
        o = OverlayItem(
            id="w1",
            level=OverlayLevel.WORD,
            bbox=(100, 200, 50, 30),
            polygon=[(100, 200), (150, 200), (150, 230), (100, 230)],
        )
        assert len(o.polygon) == 4

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OverlayItem(id="", level=OverlayLevel.WORD, bbox=(0, 0, 10, 10))

    def test_confidence_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            OverlayItem(
                id="w1",
                level=OverlayLevel.WORD,
                bbox=(0, 0, 10, 10),
                confidence=2.0,
            )


class TestInspectionData:
    def test_valid(self) -> None:
        insp = InspectionData(
            id="w1",
            level=OverlayLevel.WORD,
            text="Bonjour",
            bbox=(110, 220, 90, 40),
            confidence=0.96,
            lang="fra",
            provenance_type=EvidenceType.PROVIDER_NATIVE,
            provenance_provider="paddleocr",
            geometry_status=GeometryStatus.EXACT,
            readiness=ReadinessLevel.FULL,
        )
        assert insp.lang == "fra"


class TestViewerProjection:
    def test_valid_minimal(self) -> None:
        vp = ViewerProjection(
            image_ref="test.png",
            image_width=2480,
            image_height=3508,
        )
        assert vp.block_overlays == []
        assert vp.word_overlays == []

    def test_valid_with_overlays(self) -> None:
        block = OverlayItem(
            id="tb1",
            level=OverlayLevel.BLOCK,
            bbox=(100, 200, 1200, 900),
            label="body",
        )
        word = OverlayItem(
            id="w1",
            level=OverlayLevel.WORD,
            bbox=(110, 220, 90, 40),
            text="Bonjour",
        )
        vp = ViewerProjection(
            image_ref="test.png",
            image_width=2480,
            image_height=3508,
            block_overlays=[block],
            word_overlays=[word],
            inspection_index={
                "w1": InspectionData(
                    id="w1",
                    level=OverlayLevel.WORD,
                    text="Bonjour",
                    bbox=(110, 220, 90, 40),
                )
            },
        )
        assert len(vp.block_overlays) == 1
        assert len(vp.word_overlays) == 1
        assert "w1" in vp.inspection_index

    def test_zero_dimensions_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ViewerProjection(
                image_ref="test.png",
                image_width=0,
                image_height=100,
            )

    def test_default_export_status(self) -> None:
        vp = ViewerProjection(
            image_ref="test.png",
            image_width=100,
            image_height=100,
        )
        assert vp.export_status.alto_export == ReadinessLevel.NONE

    def test_json_roundtrip(self) -> None:
        vp = ViewerProjection(
            image_ref="test.png",
            image_width=2480,
            image_height=3508,
            export_status=ExportEligibility(
                alto_export=ReadinessLevel.FULL,
                page_export=ReadinessLevel.PARTIAL,
                viewer_render=ReadinessLevel.FULL,
            ),
        )
        data = vp.model_dump(mode="json")
        vp2 = ViewerProjection.model_validate(data)
        assert vp2.export_status.alto_export == ReadinessLevel.FULL
