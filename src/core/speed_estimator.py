"""Vehicle Speed Estimation Module for AutoGuardian.

Estimates vehicle speed in km/h based on tracking centroid displacement,
time intervals, and pixel-to-meter camera calibration.
"""

from __future__ import annotations

import collections
from typing import Deque, Dict, Optional, Tuple
import numpy as np

from src.utils.geometry import euclidean_distance


class SpeedEstimator:
    """Estimates speed (km/h) for tracked vehicles across consecutive video frames."""

    def __init__(
        self,
        pixels_per_meter: float = 12.0,
        min_history_points: int = 4,
        max_history_points: int = 12,
        enabled: bool = True,
    ) -> None:
        """Initializes the SpeedEstimator.

        Args:
            pixels_per_meter: Calibration factor relating pixel displacement to physical meters.
            min_history_points: Minimum tracked positions required before estimating speed.
            max_history_points: Maximum number of recent positions retained.
            enabled: Whether speed estimation is active.
        """
        self.pixels_per_meter = max(0.5, float(pixels_per_meter))
        self.min_history_points = min_history_points
        self.max_history_points = max_history_points
        self.enabled = enabled

        # track_id -> deque of (x, y, timestamp)
        self._history: Dict[int, Deque[Tuple[float, float, float]]] = {}
        # track_id -> smoothed speed km/h
        self._current_speeds: Dict[int, float] = {}

    def set_pixels_per_meter(self, ppm: float) -> None:
        """Dynamically updates the calibration ratio (pixels per meter)."""
        self.pixels_per_meter = max(0.5, float(ppm))

    def update(
        self,
        track_id: int,
        centroid: Tuple[int, int],
        timestamp: float,
    ) -> Optional[float]:
        """Updates position history and estimates smoothed speed in km/h.

        Args:
            track_id: Unique vehicle ID.
            centroid: Current (cx, cy) coordinate.
            timestamp: Current frame timestamp in seconds.

        Returns:
            Estimated speed in km/h or None if insufficient history.
        """
        if not self.enabled or track_id is None:
            return None

        if track_id not in self._history:
            self._history[track_id] = collections.deque(maxlen=self.max_history_points)

        hist = self._history[track_id]
        hist.append((float(centroid[0]), float(centroid[1]), float(timestamp)))

        if len(hist) < self.min_history_points:
            return None

        # Calculate speed between oldest and newest point in the history window
        x_old, y_old, t_old = hist[0]
        x_new, y_new, t_new = hist[-1]

        delta_t = t_new - t_old
        if delta_t <= 0.08:  # Require at least 80ms of observation to eliminate frame jitter
            return self._current_speeds.get(track_id)

        # Distance in pixels
        pixel_distance = euclidean_distance((x_old, y_old), (x_new, y_new))

        # Stationary threshold (less than 4 pixels of drift over the window)
        if pixel_distance < 4.0:
            speed_kmh = 0.0
        else:
            # Distance in meters
            distance_meters = pixel_distance / self.pixels_per_meter
            # Speed in meters/second
            speed_mps = distance_meters / delta_t
            # Speed in km/h
            speed_kmh = speed_mps * 3.6

            # Realistic clamp for highway & urban traffic (0 to 125 km/h)
            speed_kmh = max(0.0, min(125.0, speed_kmh))

        # Apply exponential moving average (EMA) smoothing
        if track_id in self._current_speeds:
            smoothed = 0.70 * self._current_speeds[track_id] + 0.30 * speed_kmh
        else:
            smoothed = speed_kmh

        self._current_speeds[track_id] = round(smoothed, 1)
        return self._current_speeds[track_id]

    def get_speed(self, track_id: int) -> Optional[float]:
        """Retrieves latest estimated speed for a given track_id."""
        return self._current_speeds.get(track_id)

    def remove_track(self, track_id: int) -> None:
        """Removes tracking data when vehicle leaves frame."""
        self._history.pop(track_id, None)
        self._current_speeds.pop(track_id, None)

    def reset(self) -> None:
        """Clears all tracking histories and speed records."""
        self._history.clear()
        self._current_speeds.clear()
