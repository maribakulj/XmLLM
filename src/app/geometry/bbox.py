"""BBox operations — pure functions operating on bbox tuples.

All bboxes follow the canonical convention: (x, y, width, height).
x = left edge, y = top edge, width > 0, height > 0.
"""

from __future__ import annotations

# Type alias for the canonical bbox tuple
BBoxTuple = tuple[float, float, float, float]


def x2(bbox: BBoxTuple) -> float:
    """Right edge of the bbox."""
    return bbox[0] + bbox[2]


def y2(bbox: BBoxTuple) -> float:
    """Bottom edge of the bbox."""
    return bbox[1] + bbox[3]


def area(bbox: BBoxTuple) -> float:
    """Area of the bbox."""
    return bbox[2] * bbox[3]


def center(bbox: BBoxTuple) -> tuple[float, float]:
    """Center point (cx, cy) of the bbox."""
    return (bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2)


def contains(outer: BBoxTuple, inner: BBoxTuple, tolerance: float = 0.0) -> bool:
    """Check if *outer* fully contains *inner*, with optional pixel tolerance.

    A positive tolerance allows the inner bbox to exceed the outer bbox
    by up to that many pixels on each side without failing the check.
    """
    return (
        inner[0] >= outer[0] - tolerance
        and inner[1] >= outer[1] - tolerance
        and x2(inner) <= x2(outer) + tolerance
        and y2(inner) <= y2(outer) + tolerance
    )


def intersects(a: BBoxTuple, b: BBoxTuple) -> bool:
    """Check if two bboxes overlap (share any area)."""
    return not (
        x2(a) <= b[0]
        or x2(b) <= a[0]
        or y2(a) <= b[1]
        or y2(b) <= a[1]
    )


def intersection(a: BBoxTuple, b: BBoxTuple) -> BBoxTuple | None:
    """Compute the intersection bbox, or None if they don't overlap."""
    ix = max(a[0], b[0])
    iy = max(a[1], b[1])
    ix2 = min(x2(a), x2(b))
    iy2 = min(y2(a), y2(b))
    if ix2 <= ix or iy2 <= iy:
        return None
    return (ix, iy, ix2 - ix, iy2 - iy)


def union(a: BBoxTuple, b: BBoxTuple) -> BBoxTuple:
    """Compute the smallest bbox enclosing both a and b."""
    ux = min(a[0], b[0])
    uy = min(a[1], b[1])
    ux2 = max(x2(a), x2(b))
    uy2 = max(y2(a), y2(b))
    return (ux, uy, ux2 - ux, uy2 - uy)


def union_all(bboxes: list[BBoxTuple]) -> BBoxTuple:
    """Compute the smallest bbox enclosing all given bboxes.

    Raises ValueError if the list is empty.
    """
    if not bboxes:
        raise ValueError("Cannot compute union of an empty list of bboxes")
    result = bboxes[0]
    for b in bboxes[1:]:
        result = union(result, b)
    return result


def expand(bbox: BBoxTuple, margin: float) -> BBoxTuple:
    """Expand a bbox by *margin* pixels on each side.

    The result is clamped so that x and y don't go below 0.
    Width and height are always at least 1 pixel after expansion.
    """
    new_x = max(0.0, bbox[0] - margin)
    new_y = max(0.0, bbox[1] - margin)
    new_w = max(1.0, bbox[2] + 2 * margin)
    new_h = max(1.0, bbox[3] + 2 * margin)
    return (new_x, new_y, new_w, new_h)


def iou(a: BBoxTuple, b: BBoxTuple) -> float:
    """Intersection over Union of two bboxes."""
    inter = intersection(a, b)
    if inter is None:
        return 0.0
    inter_area = area(inter)
    union_area = area(a) + area(b) - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def overlap_ratio(inner: BBoxTuple, outer: BBoxTuple) -> float:
    """Fraction of *inner*'s area that overlaps with *outer*."""
    inter = intersection(inner, outer)
    if inter is None:
        return 0.0
    inner_area = area(inner)
    if inner_area <= 0:
        return 0.0
    return area(inter) / inner_area
