"""Polygon operations — conversions and validation for polygon geometry.

Polygons are represented as list[tuple[float, float]] — ordered (x, y) vertices.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.geometry.bbox import BBoxTuple

PolygonPoints = list[tuple[float, float]]


def polygon_to_bbox(polygon: PolygonPoints) -> BBoxTuple:
    """Compute the axis-aligned bounding box enclosing a polygon.

    Returns (x, y, width, height) in canonical convention.
    Raises ValueError if the polygon has fewer than 3 points.
    """
    if len(polygon) < 3:
        raise ValueError(f"A polygon needs at least 3 points, got {len(polygon)}")
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    min_x = min(xs)
    min_y = min(ys)
    max_x = max(xs)
    max_y = max(ys)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def bbox_to_polygon(bbox: BBoxTuple) -> PolygonPoints:
    """Convert a bbox to a 4-point polygon (clockwise from top-left)."""
    x, y, w, h = bbox
    return [
        (x, y),
        (x + w, y),
        (x + w, y + h),
        (x, y + h),
    ]


def polygon_area(polygon: PolygonPoints) -> float:
    """Compute area using the shoelace formula.  Always returns a positive value."""
    n = len(polygon)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        j = (i + 1) % n
        total += polygon[i][0] * polygon[j][1]
        total -= polygon[j][0] * polygon[i][1]
    return abs(total) / 2.0


def polygon_centroid(polygon: PolygonPoints) -> tuple[float, float]:
    """Compute the centroid of a polygon.

    Raises ValueError if the polygon has fewer than 3 points.
    """
    if len(polygon) < 3:
        raise ValueError(f"A polygon needs at least 3 points, got {len(polygon)}")
    n = len(polygon)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    return (cx, cy)


def validate_polygon(polygon: PolygonPoints) -> list[str]:
    """Return a list of warnings about the polygon.  Empty list = valid."""
    warnings: list[str] = []
    if len(polygon) < 3:
        warnings.append(f"Polygon has fewer than 3 points ({len(polygon)})")
        return warnings

    # Check for duplicate consecutive points
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        if polygon[i] == polygon[j]:
            warnings.append(f"Duplicate consecutive points at index {i} and {j}")

    # Check for zero area
    if polygon_area(polygon) == 0.0:
        warnings.append("Polygon has zero area (degenerate)")

    # Check for negative coordinates
    for i, (x, y) in enumerate(polygon):
        if x < 0 or y < 0:
            warnings.append(f"Negative coordinate at point {i}: ({x}, {y})")

    return warnings


def is_clockwise(polygon: PolygonPoints) -> bool:
    """Check if polygon vertices are ordered clockwise."""
    n = len(polygon)
    if n < 3:
        return False
    total = 0.0
    for i in range(n):
        j = (i + 1) % n
        total += (polygon[j][0] - polygon[i][0]) * (polygon[j][1] + polygon[i][1])
    return total > 0


def ensure_clockwise(polygon: PolygonPoints) -> PolygonPoints:
    """Return the polygon in clockwise order."""
    if not is_clockwise(polygon):
        return list(reversed(polygon))
    return polygon
