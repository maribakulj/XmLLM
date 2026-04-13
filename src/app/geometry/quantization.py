"""Quantization — float→int conversion strategies and tolerance checks.

ALTO XML expects integer coordinates.  This module provides explicit
strategies for converting float geometry to int, with configurable
rounding and tolerance for containment checks.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.geometry.bbox import BBoxTuple


class RoundingStrategy(StrEnum):
    """How to round float coordinates to integers."""

    ROUND = "round"
    FLOOR = "floor"
    CEIL = "ceil"
    EXPAND = "expand"


def quantize_value(value: float, strategy: RoundingStrategy = RoundingStrategy.ROUND) -> int:
    """Convert a single float to int using the given strategy."""
    if strategy == RoundingStrategy.ROUND:
        return round(value)
    elif strategy == RoundingStrategy.FLOOR:
        return math.floor(value)
    elif strategy == RoundingStrategy.CEIL:
        return math.ceil(value)
    elif strategy == RoundingStrategy.EXPAND:
        return round(value)
    raise ValueError(f"Unknown rounding strategy: {strategy}")


def quantize_bbox(
    bbox: BBoxTuple,
    strategy: RoundingStrategy = RoundingStrategy.ROUND,
) -> tuple[int, int, int, int]:
    """Convert a float bbox to integer coordinates.

    The EXPAND strategy rounds x,y down and width,height up to ensure
    the integer bbox fully contains the float bbox.
    """
    x, y, w, h = bbox
    if strategy == RoundingStrategy.EXPAND:
        ix = math.floor(x)
        iy = math.floor(y)
        ix2 = math.ceil(x + w)
        iy2 = math.ceil(y + h)
        return (ix, iy, ix2 - ix, iy2 - iy)
    else:
        return (
            quantize_value(x, strategy),
            quantize_value(y, strategy),
            max(1, quantize_value(w, strategy)),
            max(1, quantize_value(h, strategy)),
        )


def bbox_contains_with_tolerance(
    outer: BBoxTuple,
    inner: BBoxTuple,
    tolerance: float = 5.0,
) -> bool:
    """Check if outer contains inner with configurable pixel tolerance.

    This is the standard containment check used by the structural validator.
    The tolerance allows the inner bbox to exceed the outer bbox by up to
    *tolerance* pixels on each side.
    """
    from src.app.geometry.bbox import contains

    return contains(outer, inner, tolerance)


def compute_overflow(outer: BBoxTuple, inner: BBoxTuple) -> dict[str, float]:
    """Compute how many pixels inner overflows outer on each side.

    Returns a dict with keys 'left', 'top', 'right', 'bottom'.
    Positive values mean overflow, negative/zero means contained.
    """
    from src.app.geometry.bbox import x2, y2

    return {
        "left": outer[0] - inner[0],
        "top": outer[1] - inner[1],
        "right": x2(inner) - x2(outer),
        "bottom": y2(inner) - y2(outer),
    }


def max_overflow(outer: BBoxTuple, inner: BBoxTuple) -> float:
    """Return the maximum overflow in pixels of inner beyond outer.

    Returns 0.0 if inner is fully contained.
    """
    overflows = compute_overflow(outer, inner)
    return max(0.0, max(overflows.values()))
