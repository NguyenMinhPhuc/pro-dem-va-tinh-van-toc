"""Speed Trap Benchmark Zone Module for AutoGuardian.

Measures precise vehicle speed by timing the transition between two virtual benchmark
lines (Line A and Line B) separated by a known real-world physical distance (meters).
Emulates radar/speed trap camera systems used in ITS highways.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from src.core.detector import VehicleDetection
from src.utils.constants import (
    DEFAULT_TRAP_IN_DISTANCE,
    DEFAULT_TRAP_IN_LINE_A,
    DEFAULT_TRAP_IN_LINE_B,
    DEFAULT_TRAP_OUT_DISTANCE,
    DEFAULT_TRAP_OUT_LINE_A,
    DEFAULT_TRAP_OUT_LINE_B,
)
from src.utils.geometry import check_line_intersection


class SpeedTrapZone:
    """Calculates benchmark speed across two calibrated reference lines."""

    def __init__(
        self,
        line_a: Tuple[Tuple[int, int], Tuple[int, int]] = ((100, 200), (1180, 200)),
        line_b: Tuple[Tuple[int, int], Tuple[int, int]] = ((100, 450), (1180, 450)),
        distance_meters: float = 20.0,
        enabled: bool = True,
        name: str = "Highway Speed Trap",
    ) -> None:
        """Initializes the SpeedTrapZone.

        Args:
            line_a: ((x1, y1), (x2, y2)) coordinates for reference Line A.
            line_b: ((x1, y1), (x2, y2)) coordinates for reference Line B.
            distance_meters: Physical real-world distance (in meters) between Line A and Line B.
            enabled: Whether speed trap measuring is active.
            name: Label name for the zone.
        """
        self.line_a = line_a
        self.line_b = line_b
        self.distance_meters = max(1.0, float(distance_meters))
        self.enabled = enabled
        self.name = name

        # track_id -> timestamp when crossing Line A
        self._cross_a_time: Dict[int, float] = {}
        # track_id -> timestamp when crossing Line B
        self._cross_b_time: Dict[int, float] = {}
        # track_id -> finalized trap speed (km/h)
        self._finalized_speeds: Dict[int, float] = {}
        # track_id -> previous centroid
        self._track_history: Dict[int, Tuple[int, int]] = {}

    def update_lines(
        self,
        line_a: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        line_b: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        distance_meters: Optional[float] = None,
    ) -> None:
        """Updates line coordinates or benchmark distance."""
        if line_a is not None:
            self.line_a = line_a
        if line_b is not None:
            self.line_b = line_b
        if distance_meters is not None:
            self.distance_meters = max(1.0, float(distance_meters))

    def update(
        self,
        detections: List[VehicleDetection],
        current_time: float,
    ) -> List[Dict[str, Any]]:
        """Checks vehicle transitions between Line A and Line B and calculates trap speed.

        Args:
            detections: List of tracked vehicles in the current frame.
            current_time: Frame timestamp in seconds.

        Returns:
            List of newly finalized speed trap event dictionaries.
        """
        if not self.enabled:
            return []

        trap_events: List[Dict[str, Any]] = []

        for det in detections:
            track_id = det.track_id
            if track_id is None:
                continue

            curr_pos = det.centroid

            if track_id in self._track_history:
                prev_pos = self._track_history[track_id]

                # 1. Check intersection with Line A
                if track_id not in self._cross_a_time:
                    p1_a, p2_a = self.line_a
                    if check_line_intersection(p1_a, p2_a, prev_pos, curr_pos):
                        self._cross_a_time[track_id] = current_time

                # 2. Check intersection with Line B
                if track_id not in self._cross_b_time:
                    p1_b, p2_b = self.line_b
                    if check_line_intersection(p1_b, p2_b, prev_pos, curr_pos):
                        self._cross_b_time[track_id] = current_time

                # 3. Calculate speed if vehicle crossed both reference lines
                if (
                    track_id in self._cross_a_time
                    and track_id in self._cross_b_time
                    and track_id not in self._finalized_speeds
                ):
                    t_a = self._cross_a_time[track_id]
                    t_b = self._cross_b_time[track_id]
                    delta_t = abs(t_b - t_a)

                    if delta_t > 0.05:
                        speed_mps = self.distance_meters / delta_t
                        speed_kmh = round(speed_mps * 3.6, 1)

                        # Realistic highway clamp (5.0 to 125.0 km/h)
                        speed_kmh = max(5.0, min(125.0, speed_kmh))
                        self._finalized_speeds[track_id] = speed_kmh

                        # Direction determination
                        direction = "A_to_B" if t_a < t_b else "B_to_A"

                        event_data = {
                            "track_id": track_id,
                            "speed_kmh": speed_kmh,
                            "transit_time_seconds": round(delta_t, 3),
                            "distance_meters": self.distance_meters,
                            "direction": direction,
                            "bbox": det.bbox,
                            "class_name": det.class_name,
                        }
                        trap_events.append(event_data)

            self._track_history[track_id] = curr_pos

        # Cleanup old entries if map grows excessively
        if len(self._track_history) > 2000:
            active_ids = set(list(self._track_history.keys())[-400:])
            self._track_history = {tid: pos for tid, pos in self._track_history.items() if tid in active_ids}

        return trap_events

    def get_trap_speed(self, track_id: int) -> Optional[float]:
        """Returns finalized benchmark speed for a vehicle if available."""
        return self._finalized_speeds.get(track_id)

    def is_in_transit(self, track_id: int) -> bool:
        """Returns True if vehicle has entered Line A or B but not yet finished."""
        has_entered = (track_id in self._cross_a_time) or (track_id in self._cross_b_time)
        has_finished = track_id in self._finalized_speeds
        return has_entered and not has_finished

    def reset(self) -> None:
        """Resets all reference line records and trap speeds."""
        self._cross_a_time.clear()
        self._cross_b_time.clear()
        self._finalized_speeds.clear()
        self._track_history.clear()


class DualLaneSpeedTrap:
    """Manages two independent speed trap zones for Làn Vào (IN) and Làn Ra (OUT)."""

    def __init__(
        self,
        lane_in: Optional[SpeedTrapZone] = None,
        lane_out: Optional[SpeedTrapZone] = None,
        enabled: bool = True,
    ) -> None:
        self.lane_in = lane_in or SpeedTrapZone(
            line_a=DEFAULT_TRAP_IN_LINE_A,
            line_b=DEFAULT_TRAP_IN_LINE_B,
            distance_meters=DEFAULT_TRAP_IN_DISTANCE,
            name="Làn Vào (IN)",
            enabled=enabled,
        )
        self.lane_out = lane_out or SpeedTrapZone(
            line_a=DEFAULT_TRAP_OUT_LINE_A,
            line_b=DEFAULT_TRAP_OUT_LINE_B,
            distance_meters=DEFAULT_TRAP_OUT_DISTANCE,
            name="Làn Ra (OUT)",
            enabled=enabled,
        )
        self.enabled = enabled

    @property
    def distance_meters(self) -> float:
        """Fallback property for single-lane backward compatibility."""
        return self.lane_in.distance_meters

    @property
    def line_a(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        return self.lane_in.line_a

    @property
    def line_b(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        return self.lane_in.line_b

    def get_lane(self, lane_key: str) -> SpeedTrapZone:
        """Returns the SpeedTrapZone corresponding to 'in' or 'out'."""
        k = str(lane_key).lower()
        if "out" in k or "ra" in k:
            return self.lane_out
        return self.lane_in

    def update_lines(
        self,
        lane_key: str = "in",
        line_a: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        line_b: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        distance_meters: Optional[float] = None,
    ) -> None:
        """Updates lines or distance for a specific lane."""
        lane = self.get_lane(lane_key)
        lane.update_lines(line_a=line_a, line_b=line_b, distance_meters=distance_meters)

    def update(
        self,
        detections: List[VehicleDetection],
        current_time: float,
    ) -> List[Dict[str, Any]]:
        """Processes detections across both lanes."""
        if not self.enabled:
            return []
        events_in = self.lane_in.update(detections, current_time)
        events_out = self.lane_out.update(detections, current_time)
        for ev in events_in:
            ev["lane"] = "IN"
        for ev in events_out:
            ev["lane"] = "OUT"
        return events_in + events_out

    def get_trap_speed(self, track_id: int) -> Optional[float]:
        """Returns finalized speed from either lane."""
        return self.lane_in.get_trap_speed(track_id) or self.lane_out.get_trap_speed(track_id)

    def is_in_transit(self, track_id: int) -> bool:
        """Checks if vehicle is in transit on either lane."""
        return self.lane_in.is_in_transit(track_id) or self.lane_out.is_in_transit(track_id)

    def reset(self) -> None:
        """Resets both lane trackers."""
        self.lane_in.reset()
        self.lane_out.reset()

    def reset_to_defaults(self, lane_key: Optional[str] = None) -> None:
        """Resets specified lane or both lanes to standard default coordinates."""
        if lane_key is None or "in" in str(lane_key).lower() or "vao" in str(lane_key).lower():
            self.lane_in.update_lines(
                line_a=DEFAULT_TRAP_IN_LINE_A,
                line_b=DEFAULT_TRAP_IN_LINE_B,
                distance_meters=DEFAULT_TRAP_IN_DISTANCE,
            )
            self.lane_in.reset()
        if lane_key is None or "out" in str(lane_key).lower() or "ra" in str(lane_key).lower():
            self.lane_out.update_lines(
                line_a=DEFAULT_TRAP_OUT_LINE_A,
                line_b=DEFAULT_TRAP_OUT_LINE_B,
                distance_meters=DEFAULT_TRAP_OUT_DISTANCE,
            )
            self.lane_out.reset()
