"""Geometric helper functions for line crossing and polygon intersection tests.

Contains algorithms for:
- Point in polygon testing (winding number / ray-casting / OpenCV wrapper)
- Line segment intersection and 2D cross-product orientation
- Centroid calculations and Euclidean displacement
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np


def calculate_centroid(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Calculates the center point (cx, cy) of a bounding box [x1, y1, x2, y2].

    Args:
        bbox: Tuple of (x1, y1, x2, y2).

    Returns:
        Tuple of (center_x, center_y) as integers.
    """
    x1, y1, x2, y2 = bbox
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def calculate_bottom_center(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Calculates the bottom-center point (bcx, bcy) of a bounding box.
    Useful for vehicle ground contact point estimation.

    Args:
        bbox: Tuple of (x1, y1, x2, y2).

    Returns:
        Tuple of (bottom_center_x, bottom_center_y) as integers.
    """
    x1, y1, x2, y2 = bbox
    return int((x1 + x2) / 2), int(y2)


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Computes Euclidean distance between two 2D points.

    Args:
        p1: Point (x1, y1).
        p2: Point (x2, y2).

    Returns:
        Distance as float.
    """
    return float(np.hypot(p1[0] - p2[0], p1[1] - p2[1]))


def ccw_orientation(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    """Calculates the cross-product to determine counter-clockwise orientation of triangle ABC.

    A positive value indicates counter-clockwise turn.
    A negative value indicates clockwise turn.
    Zero indicates collinear points.

    Formula: (B.x - A.x) * (C.y - A.y) - (B.y - A.y) * (C.x - A.x)
    """
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def check_line_intersection(
    seg1_p1: Tuple[float, float],
    seg1_p2: Tuple[float, float],
    seg2_p1: Tuple[float, float],
    seg2_p2: Tuple[float, float],
) -> bool:
    """Determines whether line segment 1 (seg1_p1 -> seg1_p2) intersects with line segment 2 (seg2_p1 -> seg2_p2).

    Uses cross-product orientation tests.
    """
    d1 = ccw_orientation(seg1_p1, seg1_p2, seg2_p1)
    d2 = ccw_orientation(seg1_p1, seg1_p2, seg2_p2)
    d3 = ccw_orientation(seg2_p1, seg2_p2, seg1_p1)
    d4 = ccw_orientation(seg2_p1, seg2_p2, seg1_p2)

    # General intersection condition: endpoints straddle each other's segment lines
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True

    return False


def get_crossing_direction(
    line_p1: Tuple[float, float],
    line_p2: Tuple[float, float],
    prev_pos: Tuple[float, float],
    curr_pos: Tuple[float, float],
) -> Optional[str]:
    """Determines the direction of crossing relative to the virtual line vector (P1 -> P2).

    Returns:
        'A_to_B' if moving from positive side to negative side,
        'B_to_A' if moving from negative side to positive side,
        None if no crossing occurred.
    """
    if not check_line_intersection(line_p1, line_p2, prev_pos, curr_pos):
        return None

    # Check side of line for prev_pos and curr_pos
    prev_side = ccw_orientation(line_p1, line_p2, prev_pos)
    curr_side = ccw_orientation(line_p1, line_p2, curr_pos)

    if prev_side > 0 and curr_side <= 0:
        return "IN"
    elif prev_side < 0 and curr_side >= 0:
        return "OUT"

    return "CROSSED"


def is_point_in_polygon(point: Tuple[float, float], polygon_points: List[Tuple[float, float]]) -> bool:
    """Tests if a 2D point is inside or on the boundary of a polygon using Ray Casting.

    Args:
        point: Tuple (x, y).
        polygon_points: List of polygon vertex tuples [(x1, y1), (x2, y2), ...].

    Returns:
        True if point is inside or on the edge of polygon, False otherwise.
    """
    n = len(polygon_points)
    if n < 3:
        return False

    x, y = point
    inside = False

    p1x, p1y = polygon_points[0]
    for i in range(n + 1):
        p2x, p2y = polygon_points[i % n]
        if min(p1y, p2y) < y <= max(p1y, p2y):
            if x <= max(p1x, p2x):
                if p1y != p2y:
                    x_inters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if p1x == p2x or x <= x_inters:
                    inside = not inside
        p1x, p1y = p2x, p2y

    return inside

