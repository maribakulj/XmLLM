"""Tests for geometry/quantization.py — float→int and tolerance checks."""

from __future__ import annotations

import pytest

from src.app.geometry.quantization import (
    RoundingStrategy,
    bbox_contains_with_tolerance,
    compute_overflow,
    max_overflow,
    quantize_bbox,
    quantize_value,
)


class TestQuantizeValue:
    def test_round(self) -> None:
        assert quantize_value(10.4) == 10
        assert quantize_value(10.5) == 10  # banker's rounding
        assert quantize_value(10.6) == 11

    def test_floor(self) -> None:
        assert quantize_value(10.9, RoundingStrategy.FLOOR) == 10
        assert quantize_value(10.1, RoundingStrategy.FLOOR) == 10

    def test_ceil(self) -> None:
        assert quantize_value(10.1, RoundingStrategy.CEIL) == 11
        assert quantize_value(10.0, RoundingStrategy.CEIL) == 10


class TestQuantizeBbox:
    def test_round(self) -> None:
        result = quantize_bbox((10.3, 20.7, 100.4, 50.6))
        assert result == (10, 21, 100, 51)

    def test_floor(self) -> None:
        result = quantize_bbox((10.9, 20.9, 100.9, 50.9), RoundingStrategy.FLOOR)
        assert result == (10, 20, 100, 50)

    def test_ceil(self) -> None:
        result = quantize_bbox((10.1, 20.1, 100.1, 50.1), RoundingStrategy.CEIL)
        assert result == (11, 21, 101, 51)

    def test_expand(self) -> None:
        result = quantize_bbox((10.3, 20.7, 100.4, 50.6), RoundingStrategy.EXPAND)
        # floor(x)=10, floor(y)=20, ceil(x+w)=ceil(110.7)=111, ceil(y+h)=ceil(71.3)=72
        assert result == (10, 20, 101, 52)

    def test_min_dimension_1(self) -> None:
        """Width and height should never be 0 after quantization."""
        result = quantize_bbox((10.0, 20.0, 0.3, 0.3))
        assert result[2] >= 1
        assert result[3] >= 1

    def test_integer_input_passthrough(self) -> None:
        result = quantize_bbox((10.0, 20.0, 100.0, 50.0))
        assert result == (10, 20, 100, 50)


class TestBboxContainsWithTolerance:
    def test_contained(self) -> None:
        outer = (0.0, 0.0, 100.0, 100.0)
        inner = (10.0, 10.0, 20.0, 20.0)
        assert bbox_contains_with_tolerance(outer, inner) is True

    def test_overflow_within_tolerance(self) -> None:
        outer = (0.0, 0.0, 100.0, 100.0)
        inner = (0.0, 0.0, 103.0, 100.0)  # 3px overflow right
        assert bbox_contains_with_tolerance(outer, inner, tolerance=5.0) is True

    def test_overflow_beyond_tolerance(self) -> None:
        outer = (0.0, 0.0, 100.0, 100.0)
        inner = (0.0, 0.0, 110.0, 100.0)  # 10px overflow
        assert bbox_contains_with_tolerance(outer, inner, tolerance=5.0) is False

    def test_zero_tolerance(self) -> None:
        outer = (0.0, 0.0, 100.0, 100.0)
        inner = (0.0, 0.0, 100.1, 100.0)
        assert bbox_contains_with_tolerance(outer, inner, tolerance=0.0) is False


class TestComputeOverflow:
    def test_contained(self) -> None:
        outer = (0.0, 0.0, 100.0, 100.0)
        inner = (10.0, 10.0, 20.0, 20.0)
        ov = compute_overflow(outer, inner)
        # All values should be <= 0 (negative = well inside)
        assert ov["left"] <= 0  # outer_left=0, inner_left=10 → -10
        assert ov["top"] <= 0
        assert ov["right"] <= 0
        assert ov["bottom"] <= 0

    def test_overflow_right(self) -> None:
        outer = (0.0, 0.0, 100.0, 100.0)
        inner = (80.0, 10.0, 30.0, 20.0)  # right edge = 110
        ov = compute_overflow(outer, inner)
        assert ov["right"] == pytest.approx(10.0)

    def test_overflow_all_sides(self) -> None:
        outer = (10.0, 10.0, 80.0, 80.0)
        inner = (5.0, 5.0, 90.0, 90.0)
        ov = compute_overflow(outer, inner)
        assert ov["left"] == pytest.approx(5.0)
        assert ov["top"] == pytest.approx(5.0)
        assert ov["right"] == pytest.approx(5.0)
        assert ov["bottom"] == pytest.approx(5.0)


class TestMaxOverflow:
    def test_contained(self) -> None:
        assert max_overflow((0, 0, 100, 100), (10, 10, 20, 20)) == 0.0

    def test_overflow(self) -> None:
        assert max_overflow((0, 0, 100, 100), (0, 0, 107, 100)) == pytest.approx(7.0)

    def test_overflow_multiple_sides(self) -> None:
        assert max_overflow((10, 10, 80, 80), (5, 5, 90, 90)) == pytest.approx(5.0)
