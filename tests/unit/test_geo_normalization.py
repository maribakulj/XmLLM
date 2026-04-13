"""Tests for geometry/normalization.py — format conversions."""

from __future__ import annotations

import pytest
from src.app.geometry import normalization


class TestXyxyToXywh:
    def test_normal(self) -> None:
        result = normalization.xyxy_to_xywh((10, 20, 110, 70))
        assert result == (10, 20, 100, 50)

    def test_swapped_coords(self) -> None:
        """Some providers may swap x1/x2 or y1/y2 — we handle it."""
        result = normalization.xyxy_to_xywh((110, 70, 10, 20))
        assert result == (10, 20, 100, 50)

    def test_zero_size(self) -> None:
        result = normalization.xyxy_to_xywh((10, 10, 10, 10))
        assert result == (10, 10, 0, 0)


class TestXywhToXyxy:
    def test_normal(self) -> None:
        result = normalization.xywh_to_xyxy((10, 20, 100, 50))
        assert result == (10, 20, 110, 70)

    def test_roundtrip(self) -> None:
        original = (10, 20, 110, 70)
        xywh = normalization.xyxy_to_xywh(original)
        back = normalization.xywh_to_xyxy(xywh)
        assert back == original


class TestCxcywhToXywh:
    def test_normal(self) -> None:
        result = normalization.cxcywh_to_xywh((50, 50, 100, 80))
        assert result == (0, 10, 100, 80)

    def test_roundtrip(self) -> None:
        original = (10, 20, 100, 50)
        cxcywh = normalization.xywh_to_cxcywh(original)
        back = normalization.cxcywh_to_xywh(cxcywh)
        assert back == pytest.approx(original)


class TestFourPointToXywh:
    def test_axis_aligned(self) -> None:
        points = [[100, 200], [400, 200], [400, 250], [100, 250]]
        result = normalization.four_point_to_xywh(points)
        assert result == (100, 200, 300, 50)

    def test_rotated_quad(self) -> None:
        # Slightly rotated — bbox is the enclosing axis-aligned box
        points = [[98, 205], [402, 195], [404, 245], [100, 255]]
        result = normalization.four_point_to_xywh(points)
        assert result[0] == 98   # min x
        assert result[1] == 195  # min y
        assert result[2] == pytest.approx(306)  # max_x - min_x
        assert result[3] == pytest.approx(60)   # max_y - min_y

    def test_tuples(self) -> None:
        points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        result = normalization.four_point_to_xywh(points)
        assert result == (0, 0, 10, 10)

    def test_wrong_count(self) -> None:
        with pytest.raises(ValueError, match="4 points"):
            normalization.four_point_to_xywh([[0, 0], [1, 1]])


class TestFourPointToPolygon:
    def test_normal(self) -> None:
        points = [[100, 200], [400, 200], [400, 250], [100, 250]]
        result = normalization.four_point_to_polygon(points)
        assert result == [(100, 200), (400, 200), (400, 250), (100, 250)]

    def test_wrong_count(self) -> None:
        with pytest.raises(ValueError, match="4 points"):
            normalization.four_point_to_polygon([[0, 0]])


class TestNormalizedBbox:
    def test_to_pixels(self) -> None:
        result = normalization.normalize_bbox_to_pixels(
            (0.1, 0.2, 0.5, 0.3), 1000, 2000
        )
        assert result == (100, 400, 500, 600)

    def test_to_normalized(self) -> None:
        result = normalization.pixels_to_normalized_bbox(
            (100, 400, 500, 600), 1000, 2000
        )
        assert result == (0.1, 0.2, 0.5, 0.3)

    def test_zero_image_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            normalization.pixels_to_normalized_bbox((0, 0, 10, 10), 0, 100)

    def test_roundtrip(self) -> None:
        original = (50, 100, 200, 300)
        norm = normalization.pixels_to_normalized_bbox(original, 1000, 2000)
        back = normalization.normalize_bbox_to_pixels(norm, 1000, 2000)
        assert back == pytest.approx(original)
