"""Tests for geometry/bbox.py — pure bbox operations."""

from __future__ import annotations

import pytest

from src.app.geometry import bbox


class TestBasicProperties:
    def test_x2(self) -> None:
        assert bbox.x2((10, 20, 100, 50)) == 110

    def test_y2(self) -> None:
        assert bbox.y2((10, 20, 100, 50)) == 70

    def test_area(self) -> None:
        assert bbox.area((0, 0, 10, 20)) == 200

    def test_center(self) -> None:
        cx, cy = bbox.center((100, 200, 300, 50))
        assert cx == 250.0
        assert cy == 225.0


class TestContains:
    def test_fully_inside(self) -> None:
        outer = (0, 0, 100, 100)
        inner = (10, 10, 20, 20)
        assert bbox.contains(outer, inner) is True

    def test_same_box(self) -> None:
        b = (10, 20, 30, 40)
        assert bbox.contains(b, b) is True

    def test_exceeds_right(self) -> None:
        outer = (0, 0, 100, 100)
        inner = (80, 10, 30, 20)  # x2 = 110 > 100
        assert bbox.contains(outer, inner) is False

    def test_exceeds_bottom(self) -> None:
        outer = (0, 0, 100, 100)
        inner = (10, 85, 20, 20)  # y2 = 105 > 100
        assert bbox.contains(outer, inner) is False

    def test_tolerance_allows_small_overflow(self) -> None:
        outer = (0, 0, 100, 100)
        inner = (0, 0, 103, 100)  # 3px overflow on right
        assert bbox.contains(outer, inner, tolerance=5) is True
        assert bbox.contains(outer, inner, tolerance=2) is False

    def test_tolerance_on_all_sides(self) -> None:
        outer = (10, 10, 80, 80)
        inner = (7, 7, 86, 86)  # 3px overflow on each side
        assert bbox.contains(outer, inner, tolerance=3) is True
        assert bbox.contains(outer, inner, tolerance=2) is False


class TestIntersects:
    def test_overlapping(self) -> None:
        a = (0, 0, 50, 50)
        b = (25, 25, 50, 50)
        assert bbox.intersects(a, b) is True

    def test_not_overlapping(self) -> None:
        a = (0, 0, 10, 10)
        b = (20, 20, 10, 10)
        assert bbox.intersects(a, b) is False

    def test_touching_edge_not_overlapping(self) -> None:
        a = (0, 0, 10, 10)
        b = (10, 0, 10, 10)  # touching at x=10
        assert bbox.intersects(a, b) is False

    def test_contained(self) -> None:
        outer = (0, 0, 100, 100)
        inner = (10, 10, 20, 20)
        assert bbox.intersects(outer, inner) is True


class TestIntersection:
    def test_overlap(self) -> None:
        a = (0, 0, 50, 50)
        b = (25, 25, 50, 50)
        result = bbox.intersection(a, b)
        assert result == (25, 25, 25, 25)

    def test_no_overlap(self) -> None:
        a = (0, 0, 10, 10)
        b = (20, 20, 10, 10)
        assert bbox.intersection(a, b) is None

    def test_contained(self) -> None:
        outer = (0, 0, 100, 100)
        inner = (10, 10, 20, 20)
        result = bbox.intersection(outer, inner)
        assert result == inner


class TestUnion:
    def test_adjacent(self) -> None:
        a = (0, 0, 10, 10)
        b = (10, 0, 10, 10)
        result = bbox.union(a, b)
        assert result == (0, 0, 20, 10)

    def test_overlapping(self) -> None:
        a = (0, 0, 50, 50)
        b = (25, 25, 50, 50)
        result = bbox.union(a, b)
        assert result == (0, 0, 75, 75)

    def test_contained(self) -> None:
        outer = (0, 0, 100, 100)
        inner = (10, 10, 20, 20)
        assert bbox.union(outer, inner) == outer


class TestUnionAll:
    def test_multiple(self) -> None:
        bboxes = [(0, 0, 10, 10), (50, 50, 10, 10), (25, 25, 10, 10)]
        result = bbox.union_all(bboxes)
        assert result == (0, 0, 60, 60)

    def test_single(self) -> None:
        assert bbox.union_all([(5, 5, 10, 10)]) == (5, 5, 10, 10)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            bbox.union_all([])


class TestExpand:
    def test_normal(self) -> None:
        result = bbox.expand((10, 20, 100, 50), 5)
        assert result == (5, 15, 110, 60)

    def test_clamp_to_zero(self) -> None:
        result = bbox.expand((2, 3, 10, 10), 10)
        assert result[0] == 0
        assert result[1] == 0

    def test_min_dimension(self) -> None:
        result = bbox.expand((10, 10, 10, 10), -100)
        assert result[2] >= 1
        assert result[3] >= 1


class TestIou:
    def test_perfect_overlap(self) -> None:
        b = (0, 0, 10, 10)
        assert bbox.iou(b, b) == pytest.approx(1.0)

    def test_no_overlap(self) -> None:
        a = (0, 0, 10, 10)
        b = (20, 20, 10, 10)
        assert bbox.iou(a, b) == 0.0

    def test_partial_overlap(self) -> None:
        a = (0, 0, 10, 10)
        b = (5, 5, 10, 10)
        # intersection = (5,5,5,5) area=25, union = 100+100-25=175
        assert bbox.iou(a, b) == pytest.approx(25 / 175)


class TestOverlapRatio:
    def test_fully_inside(self) -> None:
        inner = (10, 10, 20, 20)
        outer = (0, 0, 100, 100)
        assert bbox.overlap_ratio(inner, outer) == pytest.approx(1.0)

    def test_no_overlap(self) -> None:
        a = (0, 0, 10, 10)
        b = (20, 20, 10, 10)
        assert bbox.overlap_ratio(a, b) == 0.0

    def test_half_overlap(self) -> None:
        a = (0, 0, 10, 10)
        b = (5, 0, 10, 10)
        # a ∩ b = (5,0,5,10) area=50, a area=100
        assert bbox.overlap_ratio(a, b) == pytest.approx(0.5)
