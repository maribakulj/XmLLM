"""Geometry normalization — convert provider formats to canonical format.

Providers return coordinates in various formats.  This module provides
explicit converters for each known convention.  The canonical format is
always (x, y, width, height) with origin at top_left, unit px.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.geometry.polygon import PolygonPoints, polygon_to_bbox

if TYPE_CHECKING:
    from src.app.geometry.bbox import BBoxTuple


def xyxy_to_xywh(xyxy: tuple[float, float, float, float]) -> BBoxTuple:
    """Convert (x1, y1, x2, y2) to canonical (x, y, width, height).

    Many providers (PaddleOCR rec_boxes, etc.) use this format.
    """
    x1, y1, x2, y2 = xyxy
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return (x1, y1, x2 - x1, y2 - y1)


def xywh_to_xyxy(bbox: BBoxTuple) -> tuple[float, float, float, float]:
    """Convert canonical (x, y, width, height) to (x1, y1, x2, y2)."""
    return (bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3])


def cxcywh_to_xywh(cxcywh: tuple[float, float, float, float]) -> BBoxTuple:
    """Convert center-based (cx, cy, width, height) to canonical (x, y, w, h)."""
    cx, cy, w, h = cxcywh
    return (cx - w / 2, cy - h / 2, w, h)


def xywh_to_cxcywh(bbox: BBoxTuple) -> tuple[float, float, float, float]:
    """Convert canonical (x, y, w, h) to center-based (cx, cy, w, h)."""
    return (bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2, bbox[2], bbox[3])


def four_point_to_xywh(points: list[list[float]] | list[tuple[float, float]]) -> BBoxTuple:
    """Convert a 4-point quadrilateral (e.g. PaddleOCR detection) to canonical bbox.

    PaddleOCR returns [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] — 4 corners of
    a (possibly rotated) quadrilateral.  We compute the axis-aligned
    bounding box enclosing all 4 points.
    """
    if len(points) != 4:
        raise ValueError(f"Expected 4 points, got {len(points)}")
    polygon: PolygonPoints = [(float(p[0]), float(p[1])) for p in points]
    return polygon_to_bbox(polygon)


def four_point_to_polygon(points: list[list[float]] | list[tuple[float, float]]) -> PolygonPoints:
    """Convert a 4-point list to a PolygonPoints list."""
    if len(points) != 4:
        raise ValueError(f"Expected 4 points, got {len(points)}")
    return [(float(p[0]), float(p[1])) for p in points]


def normalize_bbox_to_pixels(
    bbox: BBoxTuple,
    image_width: int,
    image_height: int,
) -> BBoxTuple:
    """Convert a normalized [0,1] bbox to pixel coordinates."""
    return (
        bbox[0] * image_width,
        bbox[1] * image_height,
        bbox[2] * image_width,
        bbox[3] * image_height,
    )


def pixels_to_normalized_bbox(
    bbox: BBoxTuple,
    image_width: int,
    image_height: int,
) -> BBoxTuple:
    """Convert pixel bbox to normalized [0,1] coordinates."""
    if image_width <= 0 or image_height <= 0:
        raise ValueError(
            f"Image dimensions must be > 0, got {image_width}x{image_height}"
        )
    return (
        bbox[0] / image_width,
        bbox[1] / image_height,
        bbox[2] / image_width,
        bbox[3] / image_height,
    )
