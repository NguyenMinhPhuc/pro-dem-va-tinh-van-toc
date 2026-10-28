"""Virtual Line Crossing and Vehicle Counting Analytics for AutoGuardian.

Implements line intersection with vector cross-product orientation to detect
inbound/outbound vehicle crossings and strictly ensures each Track ID is counted once.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
from src.core.detector import VehicleDetection
from src.utils.geometry import check_line_intersection, get_crossing_direction


class LineCrossingCounter:
    """Detects and counts vehicles crossing a virtual boundary line."""

    def __init__(
        self,
        p1: Tuple[int, int] = (100, 360),
        p2: Tuple[int, int] = (1180, 360),
        name: str = "Line 1",
        enabled: bool = True,
    ) -> None:
        """Initializes the LineCrossingCounter.

        Args:
            p1: Start coordinate (x, y) of virtual line.
            p2: End coordinate (x, y) of virtual line.
            name: Label name of the line.
            enabled: Whether counting is active.
        """
        self.p1 = p1
        self.p2 = p2
        self.name = name
        self.enabled = enabled

        # History: track_id -> [previous_pos, current_pos]
        self._track_history: Dict[int, Tuple[int, int]] = {}

        # Set of counted IDs: guarantees each track ID is counted strictly ONCE
        self._counted_ids: Set[int] = set()

        # Cumulative statistics
        self._total_count: int = 0
        self._in_count: int = 0
        self._out_count: int = 0

    @property
    def total_count(self) -> int:
        """Returns total vehicles counted."""
        return self._total_count

    @property
    def in_count(self) -> int:
        """Returns vehicles counted moving inbound."""
        return self._in_count

    @property
    def out_count(self) -> int:
        """Returns vehicles counted moving outbound."""
        return self._out_count

    def update_coordinates(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> None:
        """Updates virtual line endpoints without losing counting stats."""
        self.p1 = p1
        self.p2 = p2

    def update(self, detections: List[VehicleDetection]) -> List[Dict[str, Any]]:
        """Processes detections from current frame and checks for line crossings.

        Args:
            detections: List of tracked vehicle detections in current frame.

        Returns:
            List of newly triggered crossing event dictionaries for logging.
        """
        if not self.enabled:
            return []

        triggered_events: List[Dict[str, Any]] = []
        current_frame_ids: Set[int] = set()

        for det in detections:
            track_id = det.track_id
            if track_id is None:
                continue

            current_frame_ids.add(track_id)
            current_pos = det.centroid

            if track_id in self._track_history:
                prev_pos = self._track_history[track_id]

                # If track ID has NOT been counted yet
                if track_id not in self._counted_ids:
                    if check_line_intersection(self.p1, self.p2, prev_pos, current_pos):
                        direction = get_crossing_direction(self.p1, self.p2, prev_pos, current_pos) or "CROSSED"

                        # Register count
                        self._counted_ids.add(track_id)
                        self._total_count += 1
                        if direction == "IN":
                            self._in_count += 1
                        elif direction == "OUT":
                            self._out_count += 1

                        event_data = {
                            "track_id": track_id,
                            "class_name": det.class_name,
                            "confidence": det.confidence,
                            "direction": direction,
                            "bbox": det.bbox,
                            "line_name": self.name,
                        }
                        triggered_events.append(event_data)

            # Update position history
            self._track_history[track_id] = current_pos

        # Purge stale tracks that haven't been seen for a long time if dictionary grows too large
        if len(self._track_history) > 2000:
            active_limit = set(list(self._track_history.keys())[-500:])
            self._track_history = {tid: pos for tid, pos in self._track_history.items() if tid in active_limit}

        return triggered_events

    def reset(self) -> None:
        """Resets the counter and clears history."""
        self._total_count = 0
        self._in_count = 0
        self._out_count = 0
        self._counted_ids.clear()
        self._track_history.clear()

