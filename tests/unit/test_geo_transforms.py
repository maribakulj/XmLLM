"""Tests for geometry/transforms.py — coordinate transformations."""

from __future__ import annotations

import pytest
from src.app.geometry import transforms


class TestRescaleBbox:
    def test_upscale(self) -> None:
        result = transforms.rescale_bbox((10, 20, 100, 50), 2.0)
        assert result == (20, 40, 200, 100)

    def test_downscale(self) -> None:
        result = transforms.rescale_bbox((10, 20, 100, 50), 0.5)
        assert result == (5, 10, 50, 25)

    def test_identity(self) -> None:
        b = (10, 20, 100, 50)
        assert transforms.rescale_bbox(b, 1.0) == b

    def test_zero_factor_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            transforms.rescale_bbox((0, 0, 10, 10), 0)

    def test_negative_factor_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            transforms.rescale_bbox((0, 0, 10, 10), -1)


class TestRescalePolygon:
    def test_upscale(self) -> None:
        poly = [(10, 20), (30, 20), (30, 40), (10, 40)]
        result = transforms.rescale_polygon(poly, 2.0)
        assert result == [(20, 40), (60, 40), (60, 80), (20, 80)]

    def test_zero_rejected(self) -> None:
        with pytest.raises(ValueError):
            transforms.rescale_polygon([(0, 0)], 0)


class TestClipBboxToPage:
    def test_already_inside(self) -> None:
        result = transforms.clip_bbox_to_page((10, 20, 50, 30), 100, 100)
        assert result == (10, 20, 50, 30)

    def test_overflow_right(self) -> None:
        result = transforms.clip_bbox_to_page((80, 10, 50, 20), 100, 100)
        # x=80, x2=130, clipped to x2=100, so w=20
        assert result == (80, 10, 20, 20)

    def test_overflow_bottom(self) -> None:
        result = transforms.clip_bbox_to_page((10, 85, 20, 30), 100, 100)
        assert result == (10, 85, 20, 15)

    def test_negative_origin(self) -> None:
        result = transforms.clip_bbox_to_page((-5, -10, 50, 50), 100, 100)
        assert result[0] == 0
        assert result[1] == 0

    def test_min_dimension_1(self) -> None:
        # bbox entirely outside right edge
        result = transforms.clip_bbox_to_page((200, 50, 10, 10), 100, 100)
        assert result[2] >= 1
        assert result[3] >= 1


class TestClipPolygonToPage:
    def test_clamp(self) -> None:
        poly = [(-5, -10), (150, -10), (150, 120), (-5, 120)]
        result = transforms.clip_polygon_to_page(poly, 100, 100)
        assert result == [(0, 0), (100, 0), (100, 100), (0, 100)]


class TestRotateBbox90:
    def test_once(self) -> None:
        # Page 100x200, bbox at (10, 20, 30, 40)
        # After 90° CW: new_x = 200 - 20 - 40 = 140, new_y = 10
        # w and h swap: w=40, h=30
        result = transforms.rotate_bbox_90((10, 20, 30, 40), 100, 200, times=1)
        assert result == (140, 10, 40, 30)

    def test_twice(self) -> None:
        # 180°: (page_w - x - w, page_h - y - h, w, h)
        result = transforms.rotate_bbox_90((10, 20, 30, 40), 100, 200, times=2)
        assert result == (60, 140, 30, 40)

    def test_four_times_identity(self) -> None:
        b = (10, 20, 30, 40)
        result = transforms.rotate_bbox_90(b, 100, 200, times=4)
        assert result == pytest.approx(b)

    def test_zero_times_identity(self) -> None:
        b = (10, 20, 30, 40)
        result = transforms.rotate_bbox_90(b, 100, 200, times=0)
        assert result == b


class TestRescalePoint:
    def test_upscale(self) -> None:
        assert transforms.rescale_point((10, 20), 2.0) == (20, 40)

    def test_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            transforms.rescale_point((10, 20), 0)


class TestRotatePoint90:
    def test_once(self) -> None:
        # Page 100x200, point (10, 20) → (200 - 20, 10) = (180, 10)
        assert transforms.rotate_point_90((10, 20), 100, 200, times=1) == (180, 10)

    def test_four_times_identity(self) -> None:
        p = (10, 20)
        result = transforms.rotate_point_90(p, 100, 200, times=4)
        assert result == pytest.approx(p)

    def test_zero_times_identity(self) -> None:
        p = (10, 20)
        assert transforms.rotate_point_90(p, 100, 200, times=0) == p


class TestRotatePolygon90:
    def test_rotates_all_points(self) -> None:
        poly = [(0, 0), (10, 0), (10, 10), (0, 10)]
        result = transforms.rotate_polygon_90(poly, 100, 200, times=1)
        assert len(result) == 4
        # Check first point: (0,0) → (200-0, 0) = (200, 0)
        assert result[0] == (200, 0)

    def test_four_times_identity(self) -> None:
        poly = [(10, 20), (30, 20), (30, 40), (10, 40)]
        result = transforms.rotate_polygon_90(poly, 100, 200, times=4)
        for orig, rotated in zip(poly, result, strict=True):
            assert rotated == pytest.approx(orig)


class TestTranslate:
    def test_bbox(self) -> None:
        result = transforms.translate_bbox((10, 20, 30, 40), 5, -10)
        assert result == (15, 10, 30, 40)

    def test_polygon(self) -> None:
        poly = [(0, 0), (10, 0), (10, 10)]
        result = transforms.translate_polygon(poly, 100, 200)
        assert result == [(100, 200), (110, 200), (110, 210)]
