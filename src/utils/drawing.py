"""Drawing and visual overlay utility functions for AutoGuardian.

Provides clean, anti-aliased visual annotations for:
- Object bounding boxes with class and track ID badges
- Virtual counting lines with directional arrows
- Parking ROI polygons with violation warning colors
- FPS and dashboard stat counters
- Blinking REC recording indicators
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.utils.constants import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    DEFAULT_BOX_THICKNESS,
    DEFAULT_FONT_SCALE,
    DEFAULT_FONT_THICKNESS,
    DEFAULT_LINE_THICKNESS,
)


def strip_vietnamese_diacritics(text: str) -> str:
    """Strips Vietnamese tone marks to prevent Hershey font glyph corruption in OpenCV."""
    vietnamese_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
        'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
        'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
        'Đ': 'D',
        'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
        'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
        'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
        'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
        'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
        'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
        'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
        'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y'
    }
    return "".join(vietnamese_map.get(ch, ch) for ch in text)


def draw_detection_box(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    track_id: Optional[int] = None,
    class_name: str = "car",
    confidence: Optional[float] = None,
    color: Tuple[int, int, int] = COLOR_CYAN,
    show_id: bool = True,
    speed_kmh: Optional[float] = None,
    license_plate: Optional[str] = None,
) -> None:
    """Draws a styled bounding box with label badge on the frame.

    Args:
        frame: BGR image.
        bbox: (x1, y1, x2, y2).
        track_id: Tracking ID if available.
        class_name: Detected object class.
        confidence: Confidence score (0.0 to 1.0).
        color: Box BGR color.
        show_id: Whether to display track_id.
        speed_kmh: Estimated speed in km/h if available.
        license_plate: Recognized plate text if available.
    """
    x1, y1, x2, y2 = bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, DEFAULT_BOX_THICKNESS)

    # Build badge label
    parts = []
    if show_id and track_id is not None:
        parts.append(f"#{track_id}")
    parts.append(class_name)

    if license_plate:
        parts.append(f"[{license_plate}]")

    if speed_kmh is not None and speed_kmh > 0:
        parts.append(f"{speed_kmh:.0f} km/h")

    if confidence is not None:
        parts.append(f"{confidence:.2f}")

    label = " | ".join(parts)
    (text_w, text_h), baseline = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, DEFAULT_FONT_SCALE, DEFAULT_FONT_THICKNESS
    )

    badge_top = max(0, y1 - text_h - 8)
    badge_bottom = y1
    badge_right = min(frame.shape[1], x1 + text_w + 8)

    # Draw solid background badge
    cv2.rectangle(frame, (x1, badge_top), (badge_right, badge_bottom), color, -1)

    # Determine contrasting text color
    text_color = COLOR_BLACK if (color[0] + color[1] + color[2]) > 380 else COLOR_WHITE
    cv2.putText(
        frame,
        label,
        (x1 + 4, badge_bottom - 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        DEFAULT_FONT_SCALE,
        text_color,
        DEFAULT_FONT_THICKNESS,
        cv2.LINE_AA,
    )


def draw_virtual_line(
    frame: np.ndarray,
    p1: Tuple[int, int],
    p2: Tuple[int, int],
    label: str = "Counting Line",
    color: Tuple[int, int, int] = COLOR_YELLOW,
    count: Optional[int] = None,
) -> None:
    """Draws the virtual counting line with endpoints and label.

    Args:
        frame: BGR image.
        p1: Start point (x, y).
        p2: End point (x, y).
        label: Text label for the line.
        color: BGR line color.
        count: Current crossing count.
    """
    cv2.line(frame, p1, p2, color, DEFAULT_LINE_THICKNESS + 1, cv2.LINE_AA)
    cv2.circle(frame, p1, 5, color, -1, cv2.LINE_AA)
    cv2.circle(frame, p2, 5, color, -1, cv2.LINE_AA)

    mid_x = int((p1[0] + p2[0]) / 2)
    mid_y = int((p1[1] + p2[1]) / 2)

    text = f"{label}: {count}" if count is not None else label
    text = strip_vietnamese_diacritics(text)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)

    # Text background
    cv2.rectangle(
        frame,
        (mid_x - int(tw / 2) - 4, mid_y - th - 8),
        (mid_x + int(tw / 2) + 4, mid_y + 2),
        COLOR_BLACK,
        -1,
    )
    cv2.putText(
        frame,
        text,
        (mid_x - int(tw / 2), mid_y - 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        1,
        cv2.LINE_AA,
    )


def draw_speed_trap_zone(
    frame: np.ndarray,
    line_a: Tuple[Tuple[int, int], Tuple[int, int]],
    line_b: Tuple[Tuple[int, int], Tuple[int, int]],
    distance_meters: float = 20.0,
    lane_name: str = "",
    color_a: Optional[Tuple[int, int, int]] = None,
    color_b: Optional[Tuple[int, int, int]] = None,
) -> None:
    """Draws the two benchmark lines for the Speed Trap Highway measurement zone.

    Args:
        frame: BGR image.
        line_a: ((x1, y1), (x2, y2)) for benchmark Line A.
        line_b: ((x1, y1), (x2, y2)) for benchmark Line B.
        distance_meters: Calibrated physical distance in meters.
        lane_name: Optional lane title (e.g. "VÀO", "RA").
        color_a: Optional BGR color for Line A.
        color_b: Optional BGR color for Line B.
    """
    p1_a, p2_a = line_a
    p1_b, p2_b = line_b

    # Draw Line A
    c_a = color_a if color_a is not None else (255, 200, 0)
    cv2.line(frame, p1_a, p2_a, c_a, 2, cv2.LINE_AA)
    cv2.circle(frame, p1_a, 4, c_a, -1)
    cv2.circle(frame, p2_a, 4, c_a, -1)

    clean_lane = strip_vietnamese_diacritics(lane_name).upper()
    mid_a = (int((p1_a[0] + p2_a[0]) / 2), int((p1_a[1] + p2_a[1]) / 2))
    label_a = f"MOC A ({clean_lane})" if clean_lane else "MOC A (BAT DAU)"
    (tw_a, th_a), _ = cv2.getTextSize(label_a, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.rectangle(frame, (mid_a[0] - int(tw_a/2) - 4, mid_a[1] - th_a - 6), (mid_a[0] + int(tw_a/2) + 4, mid_a[1] + 2), COLOR_BLACK, -1)
    cv2.putText(frame, label_a, (mid_a[0] - int(tw_a/2), mid_a[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c_a, 1, cv2.LINE_AA)

    # Draw Line B
    c_b = color_b if color_b is not None else (0, 255, 128)
    cv2.line(frame, p1_b, p2_b, c_b, 2, cv2.LINE_AA)
    cv2.circle(frame, p1_b, 4, c_b, -1)
    cv2.circle(frame, p2_b, 4, c_b, -1)

    mid_b = (int((p1_b[0] + p2_b[0]) / 2), int((p1_b[1] + p2_b[1]) / 2))
    label_b = f"MOC B ({clean_lane}: {distance_meters:.0f}m)" if clean_lane else f"MOC B (KET THUC: {distance_meters:.0f}m)"
    (tw_b, th_b), _ = cv2.getTextSize(label_b, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.rectangle(frame, (mid_b[0] - int(tw_b/2) - 4, mid_b[1] - th_b - 6), (mid_b[0] + int(tw_b/2) + 4, mid_b[1] + 2), COLOR_BLACK, -1)
    cv2.putText(frame, label_b, (mid_b[0] - int(tw_b/2), mid_b[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c_b, 1, cv2.LINE_AA)

    # Connect corridor with faint dashed lines
    cv2.line(frame, p1_a, p1_b, (120, 120, 120), 1, cv2.LINE_AA)
    cv2.line(frame, p2_a, p2_b, (120, 120, 120), 1, cv2.LINE_AA)


def draw_roi_polygon(
    frame: np.ndarray,
    points: List[Tuple[int, int]],
    name: str = "Parking ROI",
    is_violating: bool = False,
    active_vehicles_count: int = 0,
) -> None:
    """Draws a semi-transparent polygon ROI for the parking monitoring zone.

    Args:
        frame: BGR image.
        points: List of polygon vertices [(x, y), ...].
        name: Name of the zone.
        is_violating: If True, highlight with alert red overlay.
        active_vehicles_count: Number of vehicles currently inside.
    """
    if len(points) < 3:
        return

    pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
    base_color = COLOR_RED if is_violating else COLOR_GREEN

    # Create semi-transparent overlay
    overlay = frame.copy()
    cv2.fillPoly(overlay, [pts], base_color)
    alpha = 0.25 if is_violating else 0.15
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    # Draw solid border
    cv2.polylines(frame, [pts], isClosed=True, color=base_color, thickness=2, lineType=cv2.LINE_AA)

    # Draw vertex handles
    for pt in points:
        cv2.circle(frame, tuple(pt), 4, base_color, -1, cv2.LINE_AA)

    # Zone label at the centroid of polygon
    cx = int(np.mean([p[0] for p in points]))
    cy = int(np.mean([p[1] for p in points]))

    status_text = f"{name} ({active_vehicles_count} xe)"
    if is_violating:
        status_text += " [CANH BAO VI PHAM!]"
    status_text = strip_vietnamese_diacritics(status_text)

    (tw, th), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(
        frame,
        (cx - int(tw / 2) - 4, cy - th - 6),
        (cx + int(tw / 2) + 4, cy + 4),
        COLOR_BLACK,
        -1,
    )
    cv2.putText(
        frame,
        status_text,
        (cx - int(tw / 2), cy - 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        base_color,
        1,
        cv2.LINE_AA,
    )


def draw_rec_badge(frame: np.ndarray, blink_on: bool = True) -> None:
    """Draws a blinking 'REC' indicator on the top-right corner of the video.

    Args:
        frame: BGR image.
        blink_on: Controls blinking animation state.
    """
    if not blink_on:
        return

    h, w = frame.shape[:2]
    badge_x = w - 100
    badge_y = 35

    # Red dot
    cv2.circle(frame, (badge_x, badge_y), 7, COLOR_RED, -1, cv2.LINE_AA)
    cv2.putText(
        frame,
        "REC",
        (badge_x + 15, badge_y + 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        COLOR_RED,
        2,
        cv2.LINE_AA,
    )


def draw_dashboard_stats(
    frame: np.ndarray,
    fps: float,
    total_count: int,
    violation_count: int,
    show_fps: bool = True,
) -> None:
    """Draws top-left status banner with FPS and real-time counts.

    Args:
        frame: BGR image.
        fps: Current processed frames per second.
        total_count: Cumulative vehicle count.
        violation_count: Cumulative violations detected.
        show_fps: Whether to render FPS string.
    """
    h_box = 36
    w_box = 320 if show_fps else 240
    cv2.rectangle(frame, (10, 10), (10 + w_box, 10 + h_box), COLOR_BLACK, -1)
    cv2.rectangle(frame, (10, 10), (10 + w_box, 10 + h_box), COLOR_YELLOW, 1)

    text_parts = []
    if show_fps:
        text_parts.append(f"FPS: {fps:.1f}")
    text_parts.append(f"Xe: {total_count}")
    text_parts.append(f"Vi pham: {violation_count}")

    banner_str = " | ".join(text_parts)
    cv2.putText(
        frame,
        banner_str,
        (20, 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        COLOR_WHITE,
        1,
        cv2.LINE_AA,
    )

