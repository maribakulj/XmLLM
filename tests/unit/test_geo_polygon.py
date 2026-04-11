"""Tests for geometry/polygon.py — polygon operations."""

from __future__ import annotations

import pytest

from src.app.geometry import polygon


class TestPolygonToBbox:
    def test_rectangle(self) -> None:
        poly = [(100, 200), (400, 200), (400, 250), (100, 250)]
        result = polygon.polygon_to_bbox(poly)
        assert result == (100, 200, 300, 50)

    def test_triangle(self) -> None:
        poly = [(0, 0), (100, 0), (50, 80)]
        result = polygon.polygon_to_bbox(poly)
        assert result == (0, 0, 100, 80)

    def test_too_few_points(self) -> None:
        with pytest.raises(ValueError, match="at least 3"):
            polygon.polygon_to_bbox([(0, 0), (1, 1)])


class TestBboxToPolygon:
    def test_rectangle(self) -> None:
        result = polygon.bbox_to_polygon((10, 20, 100, 50))
        assert result == [(10, 20), (110, 20), (110, 70), (10, 70)]

    def test_roundtrip(self) -> None:
        original = (10, 20, 100, 50)
        poly = polygon.bbox_to_polygon(original)
        back = polygon.polygon_to_bbox(poly)
        assert back == original


class TestPolygonArea:
    def test_unit_square(self) -> None:
        poly = [(0, 0), (1, 0), (1, 1), (0, 1)]
        assert polygon.polygon_area(poly) == pytest.approx(1.0)

    def test_rectangle(self) -> None:
        poly = [(0, 0), (10, 0), (10, 5), (0, 5)]
        assert polygon.polygon_area(poly) == pytest.approx(50.0)

    def test_triangle(self) -> None:
        poly = [(0, 0), (10, 0), (5, 8)]
        assert polygon.polygon_area(poly) == pytest.approx(40.0)

    def test_too_few_points(self) -> None:
        assert polygon.polygon_area([(0, 0)]) == 0.0


class TestPolygonCentroid:
    def test_square(self) -> None:
        poly = [(0, 0), (10, 0), (10, 10), (0, 10)]
        cx, cy = polygon.polygon_centroid(poly)
        assert cx == pytest.approx(5.0)
        assert cy == pytest.approx(5.0)

    def test_too_few(self) -> None:
        with pytest.raises(ValueError, match="at least 3"):
            polygon.polygon_centroid([(0, 0)])


class TestValidatePolygon:
    def test_valid_polygon(self) -> None:
        poly = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert polygon.validate_polygon(poly) == []

    def test_too_few_points(self) -> None:
        warnings = polygon.validate_polygon([(0, 0)])
        assert any("fewer than 3" in w for w in warnings)

    def test_duplicate_consecutive(self) -> None:
        poly = [(0, 0), (10, 0), (10, 0), (0, 10)]
        warnings = polygon.validate_polygon(poly)
        assert any("Duplicate" in w for w in warnings)

    def test_negative_coords(self) -> None:
        poly = [(-5, 0), (10, 0), (10, 10)]
        warnings = polygon.validate_polygon(poly)
        assert any("Negative" in w for w in warnings)

    def test_degenerate_line(self) -> None:
        poly = [(0, 0), (10, 0), (20, 0)]
        warnings = polygon.validate_polygon(poly)
        assert any("zero area" in w for w in warnings)


class TestClockwise:
    """In screen coordinates (y-axis down), the signed-area formula gives
    positive for CW when vertices go right-then-down (like (0,0)→(0,10)→(10,10)→(10,0)).
    """

    def test_clockwise(self) -> None:
        # In screen coords: left-down-right-up = clockwise
        cw = [(0, 0), (0, 10), (10, 10), (10, 0)]
        assert polygon.is_clockwise(cw) is True

    def test_counter_clockwise(self) -> None:
        # In screen coords: right-down-left-up = counter-clockwise
        ccw = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert polygon.is_clockwise(ccw) is False

    def test_ensure_clockwise_already(self) -> None:
        cw = [(0, 0), (0, 10), (10, 10), (10, 0)]
        result = polygon.ensure_clockwise(cw)
        assert result == cw

    def test_ensure_clockwise_reverses(self) -> None:
        ccw = [(0, 0), (10, 0), (10, 10), (0, 10)]
        result = polygon.ensure_clockwise(ccw)
        assert polygon.is_clockwise(result) is True
