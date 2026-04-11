"""Baseline operations — for text line baselines.

A baseline is defined by a sequence of points, typically from left to right.
"""

from __future__ import annotations


BaselinePoints = list[tuple[float, float]]


def baseline_length(points: BaselinePoints) -> float:
    """Compute the total length of a baseline polyline."""
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        total += (dx * dx + dy * dy) ** 0.5
    return total


def baseline_angle(points: BaselinePoints) -> float:
    """Compute the angle (in degrees) of a baseline from start to end.

    Returns 0.0 for a horizontal baseline, positive for downward slope.
    Returns 0.0 if the baseline has fewer than 2 points.
    """
    if len(points) < 2:
        return 0.0
    import math

    dx = points[-1][0] - points[0][0]
    dy = points[-1][1] - points[0][1]
    if dx == 0 and dy == 0:
        return 0.0
    return math.degrees(math.atan2(dy, dx))


def interpolate_baseline(points: BaselinePoints, t: float) -> tuple[float, float]:
    """Interpolate a point along the baseline at parameter t in [0, 1].

    t=0 returns the start, t=1 returns the end.
    For multi-segment baselines, t is proportional to total arc length.
    """
    if len(points) < 2:
        if points:
            return points[0]
        raise ValueError("Cannot interpolate an empty baseline")

    t = max(0.0, min(1.0, t))
    total_len = baseline_length(points)
    if total_len == 0:
        return points[0]

    target = t * total_len
    accumulated = 0.0
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        seg_len = (dx * dx + dy * dy) ** 0.5
        if accumulated + seg_len >= target:
            frac = (target - accumulated) / seg_len if seg_len > 0 else 0.0
            return (
                points[i][0] + frac * dx,
                points[i][1] + frac * dy,
            )
        accumulated += seg_len

    return points[-1]
