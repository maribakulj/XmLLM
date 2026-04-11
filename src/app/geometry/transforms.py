"""Coordinate transformations — convert between provider space and canonical space.

All transformations are explicit and documented.  No implicit heavy conversion
is allowed in serializers (see AGENTS.md rule §5).
"""

from __future__ import annotations

import math

from src.app.geometry.bbox import BBoxTuple
from src.app.geometry.polygon import PolygonPoints


def rescale_bbox(bbox: BBoxTuple, factor: float) -> BBoxTuple:
    """Scale a bbox by a multiplicative factor.

    Used when the provider received a resized image.
    factor > 1 = upscale, factor < 1 = downscale.
    """
    if factor <= 0:
        raise ValueError(f"Scale factor must be > 0, got {factor}")
    return (
        bbox[0] * factor,
        bbox[1] * factor,
        bbox[2] * factor,
        bbox[3] * factor,
    )


def rescale_polygon(polygon: PolygonPoints, factor: float) -> PolygonPoints:
    """Scale all polygon points by a multiplicative factor."""
    if factor <= 0:
        raise ValueError(f"Scale factor must be > 0, got {factor}")
    return [(x * factor, y * factor) for x, y in polygon]


def rescale_point(point: tuple[float, float], factor: float) -> tuple[float, float]:
    """Scale a single point by a factor."""
    if factor <= 0:
        raise ValueError(f"Scale factor must be > 0, got {factor}")
    return (point[0] * factor, point[1] * factor)


def clip_bbox_to_page(
    bbox: BBoxTuple, page_width: float, page_height: float
) -> BBoxTuple:
    """Clip a bbox so it fits within page boundaries.

    Clamps x, y to [0, page_width/height] and adjusts width/height.
    Returns a bbox with width/height >= 1 (avoids degenerate boxes).
    """
    x, y, w, h = bbox
    # Clamp top-left
    cx = max(0.0, min(x, page_width - 1))
    cy = max(0.0, min(y, page_height - 1))
    # Clamp bottom-right
    cx2 = max(cx + 1, min(x + w, page_width))
    cy2 = max(cy + 1, min(y + h, page_height))
    return (cx, cy, cx2 - cx, cy2 - cy)


def clip_polygon_to_page(
    polygon: PolygonPoints, page_width: float, page_height: float
) -> PolygonPoints:
    """Clamp all polygon points to page boundaries."""
    return [
        (max(0.0, min(x, page_width)), max(0.0, min(y, page_height)))
        for x, y in polygon
    ]


def rotate_bbox_90(
    bbox: BBoxTuple, page_width: float, page_height: float, times: int = 1
) -> BBoxTuple:
    """Rotate a bbox by 90° clockwise around the page center.

    *times* = number of 90° rotations (1, 2, 3).
    page_width/height are the dimensions BEFORE rotation.
    """
    times = times % 4
    x, y, w, h = bbox
    for _ in range(times):
        # 90° clockwise: (x, y) -> (page_h - y - h, x)
        new_x = page_height - y - h
        new_y = x
        x, y, w, h = new_x, new_y, h, w
        # Swap page dimensions for next iteration
        page_width, page_height = page_height, page_width
    return (x, y, w, h)


def rotate_point_90(
    point: tuple[float, float], page_width: float, page_height: float, times: int = 1
) -> tuple[float, float]:
    """Rotate a point by 90° clockwise around the page origin."""
    times = times % 4
    x, y = point
    for _ in range(times):
        x, y = page_height - y, x
        page_width, page_height = page_height, page_width
    return (x, y)


def rotate_polygon_90(
    polygon: PolygonPoints, page_width: float, page_height: float, times: int = 1
) -> PolygonPoints:
    """Rotate all polygon points by 90° clockwise."""
    return [
        rotate_point_90(p, page_width, page_height, times) for p in polygon
    ]


def translate_bbox(bbox: BBoxTuple, dx: float, dy: float) -> BBoxTuple:
    """Translate a bbox by (dx, dy) pixels."""
    return (bbox[0] + dx, bbox[1] + dy, bbox[2], bbox[3])


def translate_polygon(polygon: PolygonPoints, dx: float, dy: float) -> PolygonPoints:
    """Translate all polygon points by (dx, dy)."""
    return [(x + dx, y + dy) for x, y in polygon]
