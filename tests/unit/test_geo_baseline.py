"""Tests for geometry/baseline.py — baseline operations."""

from __future__ import annotations

import pytest
from src.app.geometry import baseline


class TestBaselineLength:
    def test_horizontal(self) -> None:
        pts = [(0, 100), (200, 100)]
        assert baseline.baseline_length(pts) == pytest.approx(200.0)

    def test_diagonal(self) -> None:
        pts = [(0, 0), (3, 4)]
        assert baseline.baseline_length(pts) == pytest.approx(5.0)

    def test_multi_segment(self) -> None:
        pts = [(0, 0), (3, 4), (6, 0)]
        assert baseline.baseline_length(pts) == pytest.approx(10.0)

    def test_single_point(self) -> None:
        assert baseline.baseline_length([(0, 0)]) == 0.0

    def test_empty(self) -> None:
        assert baseline.baseline_length([]) == 0.0


class TestBaselineAngle:
    def test_horizontal(self) -> None:
        pts = [(0, 100), (200, 100)]
        assert baseline.baseline_angle(pts) == pytest.approx(0.0)

    def test_downward_slope(self) -> None:
        pts = [(0, 0), (100, 100)]
        assert baseline.baseline_angle(pts) == pytest.approx(45.0)

    def test_upward_slope(self) -> None:
        pts = [(0, 100), (100, 0)]
        assert baseline.baseline_angle(pts) == pytest.approx(-45.0)

    def test_single_point(self) -> None:
        assert baseline.baseline_angle([(5, 5)]) == 0.0


class TestInterpolateBaseline:
    def test_start(self) -> None:
        pts = [(0, 0), (100, 0)]
        x, y = baseline.interpolate_baseline(pts, 0.0)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(0.0)

    def test_end(self) -> None:
        pts = [(0, 0), (100, 0)]
        x, y = baseline.interpolate_baseline(pts, 1.0)
        assert x == pytest.approx(100.0)
        assert y == pytest.approx(0.0)

    def test_midpoint(self) -> None:
        pts = [(0, 0), (100, 0)]
        x, y = baseline.interpolate_baseline(pts, 0.5)
        assert x == pytest.approx(50.0)
        assert y == pytest.approx(0.0)

    def test_multi_segment(self) -> None:
        pts = [(0, 0), (50, 0), (100, 0)]
        x, y = baseline.interpolate_baseline(pts, 0.5)
        assert x == pytest.approx(50.0)

    def test_clamped_above_1(self) -> None:
        pts = [(0, 0), (100, 0)]
        x, y = baseline.interpolate_baseline(pts, 2.0)
        assert x == pytest.approx(100.0)

    def test_clamped_below_0(self) -> None:
        pts = [(10, 20), (110, 20)]
        x, y = baseline.interpolate_baseline(pts, -1.0)
        assert x == pytest.approx(10.0)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            baseline.interpolate_baseline([], 0.5)

    def test_single_point(self) -> None:
        x, y = baseline.interpolate_baseline([(42, 99)], 0.5)
        assert x == 42
        assert y == 99
