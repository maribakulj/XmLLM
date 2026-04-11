"""Geometry primitives and context for the canonical model.

Convention (non-negotiable, see AGENTS.md):
  - bbox: [x, y, width, height]  — x = left edge, y = top edge
  - coordinate origin: top_left
  - unit: px
  - polygon: list of (x, y) pairs, or None
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.app.domain.models.status import CoordinateOrigin, GeometryStatus, Unit


# -- Primitives --------------------------------------------------------------


class Point(BaseModel):
    """A 2D point in image space."""

    model_config = ConfigDict(frozen=True)

    x: float = Field(ge=0)
    y: float = Field(ge=0)


class BBox(BaseModel):
    """Axis-aligned bounding box: [x, y, width, height].

    x, y = top-left corner.  width, height > 0.
    """

    model_config = ConfigDict(frozen=True)

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)


PolygonPoints = list[tuple[float, float]]
"""Ordered list of (x, y) vertex pairs forming a closed polygon."""


class Baseline(BaseModel):
    """A baseline defined by two endpoints."""

    model_config = ConfigDict(frozen=True)

    start: Point
    end: Point


class ClipRect(BaseModel):
    """Clipping rectangle — same semantics as BBox but used for clipping ops."""

    model_config = ConfigDict(frozen=True)

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


# -- Geometry (the canonical geometry object on every node) ------------------


class Geometry(BaseModel):
    """Standardised geometry attached to every canonical node.

    bbox is always required (at least for ALTO export).
    polygon is optional — preserved when the provider supplies it.
    status indicates how the geometry was obtained.
    """

    model_config = ConfigDict(frozen=True)

    bbox: Annotated[
        tuple[float, float, float, float],
        Field(description="(x, y, width, height)"),
    ]
    polygon: PolygonPoints | None = None
    status: GeometryStatus

    @model_validator(mode="after")
    def _validate_bbox_dimensions(self) -> Geometry:
        _x, _y, w, h = self.bbox
        if w <= 0 or h <= 0:
            raise ValueError(f"bbox width and height must be > 0, got w={w}, h={h}")
        if _x < 0 or _y < 0:
            raise ValueError(f"bbox x and y must be >= 0, got x={_x}, y={_y}")
        return self


# -- GeometryContext (describes the coordinate space of a provider output) ---


class GeometryContext(BaseModel):
    """Describes the geometric context of a provider's output.

    Used by adapters to normalise provider coordinates into canonical space.
    """

    model_config = ConfigDict(frozen=True)

    source_width: int = Field(gt=0)
    source_height: int = Field(gt=0)
    provided_width: int | None = Field(default=None, gt=0)
    provided_height: int | None = Field(default=None, gt=0)
    resize_factor: float | None = Field(default=None, gt=0)
    rotation: float = 0.0
    coordinate_origin: CoordinateOrigin = CoordinateOrigin.TOP_LEFT
    unit: Unit = Unit.PX
