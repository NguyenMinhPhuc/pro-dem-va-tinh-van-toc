"""Parking Violation Analytics for AutoGuardian.

Monitors vehicles inside a customizable Polygon ROI. If a vehicle stays longer
than the allowed threshold (e.g. 30 seconds) without significant displacement,
triggers a violation event for alert display and evidence capture.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set, Tuple
import cv2
import numpy as np

from src.core.detector import VehicleDetection
from src.utils.constants import (
    DEFAULT_PARKING_DISPLACEMENT_LIMIT_PIXELS,
    DEFAULT_PARKING_TIME_LIMIT_SECONDS,
)
from src.utils.geometry import euclidean_distance, is_point_in_polygon


class ParkingViolationAnalyzer:
    """Monitors dwell time and stationary behavior in restricted parking polygon zones."""

    def __init__(
        self,
        points: Optional[List[Tuple[int, int]]] = None,
        name: str = "No Parking Zone A",
        threshold_seconds: float = DEFAULT_PARKING_TIME_LIMIT_SECONDS,
        displacement_tolerance: float = DEFAULT_PARKING_DISPLACEMENT_LIMIT_PIXELS,
        enabled: bool = True,
    ) -> None:
        """Initializes the ParkingViolationAnalyzer.

        Args:
            points: Vertices [(x1, y1), (x2, y2), ...] of ROI polygon.
            name: Label name of the zone.
            threshold_seconds: Maximum allowed dwell time before violation triggers.
            displacement_tolerance: Maximum movement distance in pixels to consider vehicle stationary.
            enabled: Whether monitoring is active.
        """
        self.points = points or [(150, 400), (500, 400), (550, 680), (100, 680)]
        self.name = name
        self.threshold_seconds = float(threshold_seconds)
        self.displacement_tolerance = float(displacement_tolerance)
        self.enabled = enabled

        # Active vehicles in ROI:
        # track_id -> dict(first_seen, last_seen, initial_pos, current_pos, is_violation_triggered, bbox, class_name)
        self._active_vehicles: Dict[int, Dict[str, Any]] = {}
        self._triggered_violation_ids: Set[int] = set()

    @property
    def active_vehicle_count(self) -> int:
        """Returns number of vehicles currently inside ROI."""
        return len(self._active_vehicles)

    @property
    def is_violating(self) -> bool:
        """Returns True if any vehicle in ROI is currently in violation status."""
        return len(self._triggered_violation_ids) > 0

    def update_polygon(self, points: List[Tuple[int, int]]) -> None:
        """Updates the ROI polygon vertices."""
        self.points = points

    def update(
        self,
        detections: List[VehicleDetection],
        current_time: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Processes current frame detections against the parking ROI polygon.

        Args:
            detections: List of tracked vehicles in current frame.
            current_time: Current timestamp in seconds (defaults to time.time()).

        Returns:
            List of newly triggered violation events for alert and evidence storage.
        """
        if not self.enabled or len(self.points) < 3:
            return []

        if current_time is None:
            current_time = time.time()

        new_violations: List[Dict[str, Any]] = []
        seen_track_ids_in_frame: Set[int] = set()

        for det in detections:
            track_id = det.track_id
            if track_id is None:
                continue

            # Check if vehicle centroid or bottom contact point is inside ROI polygon
            pos = det.centroid
            inside = is_point_in_polygon(pos, self.points)

            if inside:
                seen_track_ids_in_frame.add(track_id)

                if track_id not in self._active_vehicles:
                    # Vehicle just entered ROI
                    self._active_vehicles[track_id] = {
                        "first_seen": current_time,
                        "last_seen": current_time,
                        "initial_pos": pos,
                        "current_pos": pos,
                        "is_violation_triggered": False,
                        "bbox": det.bbox,
                        "class_name": det.class_name,
                    }
                else:
                    # Vehicle already in ROI
                    info = self._active_vehicles[track_id]
                    info["last_seen"] = current_time
                    info["current_pos"] = pos
                    info["bbox"] = det.bbox

                    dwell_time = current_time - info["first_seen"]
                    displacement = euclidean_distance(info["initial_pos"], pos)

                    # If vehicle moved significantly, reset its stationary timer
                    if displacement > self.displacement_tolerance:
                        info["first_seen"] = current_time
                        info["initial_pos"] = pos
                    else:
                        # Stationary check
                        if dwell_time >= self.threshold_seconds and not info["is_violation_triggered"]:
                            info["is_violation_triggered"] = True
                            self._triggered_violation_ids.add(track_id)

                            violation_event = {
                                "track_id": track_id,
                                "class_name": det.class_name,
                                "bbox": det.bbox,
                                "dwell_time": dwell_time,
                                "zone_name": self.name,
                                "violation_type": "PARKING_TIMEOUT",
                                "details": f"Do xe qua thoi gian quy dinh ({dwell_time:.1f}s > {self.threshold_seconds:.0f}s)",
                            }
                            new_violations.append(violation_event)

        # Remove vehicles that left the ROI or disappeared for more than 3.0 seconds
        stale_threshold = 3.0
        removed_ids = []
        for tid, info in list(self._active_vehicles.items()):
            if (current_time - info["last_seen"]) > stale_threshold:
                removed_ids.append(tid)

        for tid in removed_ids:
            self._active_vehicles.pop(tid, None)
            self._triggered_violation_ids.discard(tid)

        return new_violations

    def get_vehicle_dwell_time(self, track_id: int, current_time: Optional[float] = None) -> float:
        """Returns dwell time in seconds for a specific tracked vehicle."""
        if current_time is None:
            current_time = time.time()
        if track_id in self._active_vehicles:
            return current_time - self._active_vehicles[track_id]["first_seen"]
        return 0.0

    def reset(self) -> None:
        """Clears all tracked vehicles and violation states."""
        self._active_vehicles.clear()
        self._triggered_violation_ids.clear()

