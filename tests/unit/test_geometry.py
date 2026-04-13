"""Tests for geometry primitives and Geometry model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.app.domain.models import (
    Baseline,
    BBox,
    ClipRect,
    Geometry,
    GeometryContext,
    GeometryStatus,
    Point,
)


class TestPoint:
    def test_valid(self) -> None:
        p = Point(x=10.0, y=20.0)
        assert p.x == 10.0
        assert p.y == 20.0

    def test_origin(self) -> None:
        p = Point(x=0, y=0)
        assert p.x == 0.0

    def test_negative_x_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Point(x=-1, y=0)

    def test_negative_y_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Point(x=0, y=-1)

    def test_frozen(self) -> None:
        p = Point(x=1, y=2)
        with pytest.raises(ValidationError):
            p.x = 5  # type: ignore[misc]


class TestBBox:
    def test_valid(self) -> None:
        b = BBox(x=10, y=20, width=100, height=50)
        assert b.x2 == 110.0
        assert b.y2 == 70.0

    def test_as_tuple(self) -> None:
        b = BBox(x=10, y=20, width=100, height=50)
        assert b.as_tuple() == (10.0, 20.0, 100.0, 50.0)

    def test_zero_width_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BBox(x=0, y=0, width=0, height=10)

    def test_zero_height_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BBox(x=0, y=0, width=10, height=0)

    def test_negative_x_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BBox(x=-1, y=0, width=10, height=10)


class TestBaseline:
    def test_valid(self) -> None:
        bl = Baseline(start=Point(x=0, y=100), end=Point(x=200, y=100))
        assert bl.start.x == 0
        assert bl.end.x == 200


class TestClipRect:
    def test_valid(self) -> None:
        cr = ClipRect(x=0, y=0, width=100, height=100)
        assert cr.width == 100

    def test_zero_dimension_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ClipRect(x=0, y=0, width=0, height=100)


class TestGeometry:
    def test_valid_exact(self) -> None:
        g = Geometry(bbox=(100, 200, 300, 50), status=GeometryStatus.EXACT)
        assert g.bbox == (100, 200, 300, 50)
        assert g.polygon is None

    def test_valid_with_polygon(self) -> None:
        g = Geometry(
            bbox=(100, 200, 300, 50),
            polygon=[(100, 200), (400, 200), (400, 250), (100, 250)],
            status=GeometryStatus.EXACT,
        )
        assert len(g.polygon) == 4

    def test_zero_width_rejected(self) -> None:
        with pytest.raises(ValidationError, match="width and height must be > 0"):
            Geometry(bbox=(100, 200, 0, 50), status=GeometryStatus.EXACT)

    def test_zero_height_rejected(self) -> None:
        with pytest.raises(ValidationError, match="width and height must be > 0"):
            Geometry(bbox=(100, 200, 300, 0), status=GeometryStatus.EXACT)

    def test_negative_x_rejected(self) -> None:
        with pytest.raises(ValidationError, match="x and y must be >= 0"):
            Geometry(bbox=(-1, 200, 300, 50), status=GeometryStatus.EXACT)

    def test_negative_y_rejected(self) -> None:
        with pytest.raises(ValidationError, match="x and y must be >= 0"):
            Geometry(bbox=(100, -1, 300, 50), status=GeometryStatus.EXACT)

    def test_all_statuses_accepted(self) -> None:
        for status in GeometryStatus:
            g = Geometry(bbox=(10, 10, 10, 10), status=status)
            assert g.status == status

    def test_frozen(self) -> None:
        g = Geometry(bbox=(10, 20, 30, 40), status=GeometryStatus.EXACT)
        with pytest.raises(ValidationError):
            g.status = GeometryStatus.INFERRED  # type: ignore[misc]


class TestGeometryContext:
    def test_valid_minimal(self) -> None:
        gc = GeometryContext(source_width=2480, source_height=3508)
        assert gc.source_width == 2480
        assert gc.resize_factor is None

    def test_valid_full(self) -> None:
        gc = GeometryContext(
            source_width=2480,
            source_height=3508,
            provided_width=1240,
            provided_height=1754,
            resize_factor=0.5,
            rotation=90.0,
        )
        assert gc.resize_factor == 0.5

    def test_zero_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GeometryContext(source_width=0, source_height=100)
