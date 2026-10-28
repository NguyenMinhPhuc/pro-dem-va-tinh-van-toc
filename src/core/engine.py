"""AutoGuardian AI Processing Engine.

Coordinates YOLOv8 vehicle detection, ByteTrack tracking, virtual line crossing
analytics, parking violation detection, visual annotations, and event logging.
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from src.core.detector import VehicleDetection, YOLOVehicleDetector
from src.core.line_counter import LineCrossingCounter
from src.core.parking_analyzer import ParkingViolationAnalyzer
from src.core.plate_recognizer import LicensePlateRecognizer, PlateResult
from src.core.speed_estimator import SpeedEstimator
from src.core.speed_trap import DualLaneSpeedTrap, SpeedTrapZone
from src.storage.database import DatabaseManager
from src.storage.evidence import EvidenceManager
from src.storage.recorder import VideoRecorder
from src.utils.config import AppConfig
from src.utils.constants import (
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    FPS_CALCULATION_WINDOW,
)
from src.utils.drawing import (
    draw_dashboard_stats,
    draw_detection_box,
    draw_rec_badge,
    draw_roi_polygon,
    draw_speed_trap_zone,
    draw_virtual_line,
)


@dataclass
class EngineResult:
    """Encapsulates the output of a single frame processed by the AI engine."""

    annotated_frame: np.ndarray
    raw_frame: np.ndarray
    detections: List[VehicleDetection]
    fps: float
    total_counted: int
    in_counted: int
    out_counted: int
    active_in_roi: int
    is_parking_violation: bool
    new_crossing_events: List[Dict[str, Any]]
    new_violation_events: List[Dict[str, Any]]
    new_plates: List[PlateResult]
    new_trap_events: List[Dict[str, Any]] = None


class AutoGuardianAIEngine:
    """Central AI engine coordinating computer vision pipeline and event handlers."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        db_manager: Optional[DatabaseManager] = None,
        evidence_manager: Optional[EvidenceManager] = None,
        video_recorder: Optional[VideoRecorder] = None,
    ) -> None:
        """Initializes the AI Engine with detector, tracker, analytics and storage.

        Args:
            config: Optional AppConfig instance.
            db_manager: Optional DatabaseManager.
            evidence_manager: Optional EvidenceManager.
            video_recorder: Optional VideoRecorder.
        """
        self.config = config or AppConfig()
        self.db = db_manager or DatabaseManager(self.config.db_path)
        self.evidence = evidence_manager or EvidenceManager(self.config.captures_dir)
        self.recorder = video_recorder or VideoRecorder(self.config.recordings_dir)

        # Initialize detector
        self.detector = YOLOVehicleDetector(
            model_path=self.config.model_path,
            target_classes=self.config.target_classes,
        )

        # Initialize line counter
        line_cfg = self.config.counting_line
        p1 = tuple(line_cfg.get("p1", [100, 360]))
        p2 = tuple(line_cfg.get("p2", [1180, 360]))
        self.line_counter = LineCrossingCounter(
            p1=p1,
            p2=p2,
            name=line_cfg.get("name", "Line 1"),
            enabled=line_cfg.get("enabled", True),
        )

        # Initialize parking violation analyzer
        roi_cfg = self.config.parking_roi
        pts = [tuple(p) for p in roi_cfg.get("points", [[150, 400], [500, 400], [550, 680], [100, 680]])]
        self.parking_analyzer = ParkingViolationAnalyzer(
            points=pts,
            name=roi_cfg.get("name", "No Parking Zone A"),
            threshold_seconds=float(roi_cfg.get("threshold_seconds", 30.0)),
            displacement_tolerance=self.config.parking_displacement_tolerance,
            enabled=roi_cfg.get("enabled", True),
        )

        # Initialize speed estimator
        self.speed_estimator = SpeedEstimator(
            pixels_per_meter=self.config.pixels_per_meter,
            enabled=self.config.speed_estimation_enabled,
        )

        # Initialize license plate recognizer
        self.plate_recognizer = LicensePlateRecognizer(
            min_bbox_width=self.config.min_bbox_width_for_plate,
            enabled=self.config.plate_recognition_enabled,
        )

        # Initialize dual lane speed trap zones (Làn Vào & Làn Ra)
        trap_in_cfg = self.config.get_speed_trap_lane("in")
        trap_out_cfg = self.config.get_speed_trap_lane("out")

        lane_in_a = (tuple(trap_in_cfg.get("line_a", {}).get("p1", [100, 220])), tuple(trap_in_cfg.get("line_a", {}).get("p2", [600, 220])))
        lane_in_b = (tuple(trap_in_cfg.get("line_b", {}).get("p1", [100, 500])), tuple(trap_in_cfg.get("line_b", {}).get("p2", [600, 500])))
        lane_in_dist = float(trap_in_cfg.get("distance_meters", 20.0))

        lane_out_a = (tuple(trap_out_cfg.get("line_a", {}).get("p1", [680, 500])), tuple(trap_out_cfg.get("line_a", {}).get("p2", [1180, 500])))
        lane_out_b = (tuple(trap_out_cfg.get("line_b", {}).get("p1", [680, 220])), tuple(trap_out_cfg.get("line_b", {}).get("p2", [1180, 220])))
        lane_out_dist = float(trap_out_cfg.get("distance_meters", 20.0))

        self.speed_trap = DualLaneSpeedTrap(
            lane_in=SpeedTrapZone(line_a=lane_in_a, line_b=lane_in_b, distance_meters=lane_in_dist, name="Làn Vào (IN)"),
            lane_out=SpeedTrapZone(line_a=lane_out_a, line_b=lane_out_b, distance_meters=lane_out_dist, name="Làn Ra (OUT)"),
            enabled=self.config.speed_trap_enabled,
        )

        # Dynamic runtime settings
        self.confidence_threshold: float = self.config.default_confidence
        self.overlay_options: Dict[str, bool] = {
            "show_bbox": True,
            "show_track_id": True,
            "show_fps": True,
            "show_counting_line": True,
            "show_parking_roi": True,
            "show_speed_trap": True,
        }

        # FPS calculation state
        self._frame_times = collections.deque(maxlen=FPS_CALCULATION_WINDOW)
        self._fps: float = 0.0

        # Blinking REC badge state
        self._rec_blink_counter: int = 0

    @property
    def current_fps(self) -> float:
        """Returns the current measured processing FPS."""
        return self._fps

    def set_confidence(self, conf: float) -> None:
        """Dynamically adjusts detection confidence threshold."""
        self.confidence_threshold = max(0.05, min(0.95, float(conf)))

    def set_overlay_option(self, option_name: str, enabled: bool) -> None:
        """Toggles an overlay rendering flag."""
        self.overlay_options[option_name] = enabled

    def update_counting_line(self, p1: Tuple[int, int], p2: Tuple[int, int], enabled: bool = True) -> None:
        """Updates virtual line geometry and saves to config."""
        self.line_counter.update_coordinates(p1, p2)
        self.line_counter.enabled = enabled
        self.config.update_counting_line(p1, p2, enabled)

    def update_parking_roi(self, points: List[Tuple[int, int]], enabled: bool = True) -> None:
        """Updates parking ROI polygon geometry and saves to config."""
        self.parking_analyzer.update_polygon(points)
        self.parking_analyzer.enabled = enabled
        self.config.update_parking_roi(points, enabled)

    def update_speed_trap_line_a(self, p1: Tuple[int, int], p2: Tuple[int, int], lane_key: str = "in") -> None:
        """Updates speed trap Line A geometry for specified lane and saves to config."""
        self.speed_trap.update_lines(lane_key=lane_key, line_a=(p1, p2))
        self.config.update_speed_trap_line_a(p1, p2, lane_key=lane_key)

    def update_speed_trap_line_b(self, p1: Tuple[int, int], p2: Tuple[int, int], lane_key: str = "in") -> None:
        """Updates speed trap Line B geometry for specified lane and saves to config."""
        self.speed_trap.update_lines(lane_key=lane_key, line_b=(p1, p2))
        self.config.update_speed_trap_line_b(p1, p2, lane_key=lane_key)

    def update_speed_trap_distance(self, distance_meters: float, enabled: bool = True, lane_key: str = "in") -> None:
        """Updates speed trap physical distance for specified lane and saves to config."""
        self.speed_trap.update_lines(lane_key=lane_key, distance_meters=distance_meters)
        self.speed_trap.enabled = enabled
        self.config.update_speed_trap_distance(distance_meters, enabled, lane_key=lane_key)

    def reset_speed_trap_to_defaults(self, lane_key: Optional[str] = None) -> None:
        """Resets specified or both speed trap lanes to system default coordinates."""
        self.speed_trap.reset_to_defaults(lane_key=lane_key)
        self.config.reset_speed_traps_to_defaults()

    def reset_counters(self) -> None:
        """Resets vehicle counting, parking violation trackers, speed and plate recognizer, and clears DB."""
        self.line_counter.reset()
        self.parking_analyzer.reset()
        self.speed_estimator.reset()
        self.speed_trap.reset()
        self.plate_recognizer.reset()
        self.db.clear_all()

    def set_pixels_per_meter(self, ppm: float) -> None:
        """Updates speed estimation calibration factor."""
        self.speed_estimator.set_pixels_per_meter(ppm)

    def process_frame(self, raw_frame: np.ndarray, timestamp: Optional[float] = None) -> EngineResult:
        """Processes a single raw video frame through the full AI and analytics pipeline.

        Args:
            raw_frame: Raw BGR numpy array from video reader.
            timestamp: Video playback timestamp in seconds. If None, uses wall-clock time.

        Returns:
            EngineResult containing annotated frame, metadata, and triggered events.
        """
        now = time.time()
        self._frame_times.append(now)
        if len(self._frame_times) > 1:
            duration = self._frame_times[-1] - self._frame_times[0]
            self._fps = (len(self._frame_times) - 1) / max(0.001, duration)

        # Use synchronized video timestamp if provided, eliminating CPU compute lag
        effective_time = timestamp if timestamp is not None else now

        # 1. AI Detection & Tracking
        detections = self.detector.detect_and_track(
            raw_frame,
            confidence_threshold=self.confidence_threshold,
        )

        # 2. Speed Estimation, Speed Trap & License Plate Recognition
        new_plates: List[PlateResult] = []
        det_map: Dict[int, VehicleDetection] = {}

        # 2a. Update Speed Trap (Two reference lines)
        trap_events = self.speed_trap.update(detections, effective_time)

        for det in detections:
            if det.track_id is not None:
                det_map[det.track_id] = det
                # Estimate speed using effective video time (fallback/continuous)
                speed = self.speed_estimator.update(det.track_id, det.centroid, effective_time)
                
                # If vehicle passed Speed Trap Zone, prioritize benchmark speed
                trap_speed = self.speed_trap.get_trap_speed(det.track_id)
                if trap_speed is not None:
                    speed = trap_speed
                det.speed_kmh = speed

                # License plate recognition (Trigger-based)
                was_recognized = self.plate_recognizer.is_recognized(det.track_id)
                plate_res = self.plate_recognizer.recognize(raw_frame, det.bbox, det.track_id)
                if plate_res:
                    det.license_plate = plate_res.plate_text
                    if not was_recognized:
                        new_plates.append(plate_res)

        # 3. Line Crossing Analytics
        new_crossings = self.line_counter.update(detections)
        for ev in new_crossings:
            tid = ev["track_id"]
            matched_det = det_map.get(tid)
            lp = matched_det.license_plate if matched_det else None
            spd = matched_det.speed_kmh if matched_det else None

            ev["license_plate"] = lp
            ev["speed_kmh"] = spd

            self.db.insert_vehicle_event(
                track_id=tid,
                class_name=ev["class_name"],
                confidence=ev["confidence"],
                direction=ev["direction"],
                license_plate=lp,
                speed_kmh=spd,
                details=f"Crossed {ev.get('line_name', 'Line')}",
            )

        # 4. Parking Violation Analytics
        new_violations = self.parking_analyzer.update(detections, current_time=effective_time)
        for vi in new_violations:
            tid = vi["track_id"]
            matched_det = det_map.get(tid)
            lp = matched_det.license_plate if matched_det else None
            spd = matched_det.speed_kmh if matched_det else None

            vi["license_plate"] = lp
            vi["speed_kmh"] = spd

            # Capture evidence snapshot image
            snapshot_path = self.evidence.capture_violation(
                frame=raw_frame,
                track_id=tid,
                bbox=vi["bbox"],
                violation_type=vi["violation_type"],
            )
            vi["snapshot_path"] = snapshot_path
            self.db.insert_violation(
                track_id=tid,
                violation_type=vi["violation_type"],
                duration_seconds=vi["dwell_time"],
                license_plate=lp,
                speed_kmh=spd,
                snapshot_path=snapshot_path,
                details=vi["details"],
            )

        # 5. Visual Overlay Rendering
        annotated = raw_frame.copy()

        # Draw ROI Polygon
        if self.overlay_options.get("show_parking_roi", True) and self.parking_analyzer.enabled:
            draw_roi_polygon(
                frame=annotated,
                points=self.parking_analyzer.points,
                name=self.parking_analyzer.name,
                is_violating=self.parking_analyzer.is_violating,
                active_vehicles_count=self.parking_analyzer.active_vehicle_count,
            )

        # Draw Counting Line
        if self.overlay_options.get("show_counting_line", True) and self.line_counter.enabled:
            draw_virtual_line(
                frame=annotated,
                p1=self.line_counter.p1,
                p2=self.line_counter.p2,
                label=self.line_counter.name,
                count=self.line_counter.total_count,
            )

        # Draw Speed Trap Zones (Dual Lanes: IN & OUT)
        if self.overlay_options.get("show_speed_trap", True) and self.speed_trap.enabled:
            # 1. Lane IN
            draw_speed_trap_zone(
                frame=annotated,
                line_a=self.speed_trap.lane_in.line_a,
                line_b=self.speed_trap.lane_in.line_b,
                distance_meters=self.speed_trap.lane_in.distance_meters,
                lane_name="VÀO",
                color_a=(255, 200, 0),
                color_b=(0, 255, 128),
            )
            # 2. Lane OUT
            draw_speed_trap_zone(
                frame=annotated,
                line_a=self.speed_trap.lane_out.line_a,
                line_b=self.speed_trap.lane_out.line_b,
                distance_meters=self.speed_trap.lane_out.distance_meters,
                lane_name="RA",
                color_a=(0, 165, 255),
                color_b=(255, 105, 180),
            )

        # Draw Detection Boxes with Speed and Plate
        if self.overlay_options.get("show_bbox", True):
            show_id = self.overlay_options.get("show_track_id", True)
            for det in detections:
                box_color = COLOR_RED if det.track_id in self.parking_analyzer._triggered_violation_ids else COLOR_CYAN
                draw_detection_box(
                    frame=annotated,
                    bbox=det.bbox,
                    track_id=det.track_id,
                    class_name=det.class_name,
                    confidence=det.confidence,
                    color=box_color,
                    show_id=show_id,
                    speed_kmh=det.speed_kmh,
                    license_plate=det.license_plate,
                )

        # Draw Top Dashboard Stats
        draw_dashboard_stats(
            frame=annotated,
            fps=self._fps,
            total_count=self.line_counter.total_count,
            violation_count=len(self.parking_analyzer._triggered_violation_ids),
            show_fps=self.overlay_options.get("show_fps", True),
        )

        # Draw Blinking REC Badge if recording
        if self.recorder.is_recording:
            self._rec_blink_counter += 1
            blink_on = (self._rec_blink_counter % 20) < 12
            draw_rec_badge(annotated, blink_on=blink_on)
            self.recorder.write_frame(annotated)

        return EngineResult(
            annotated_frame=annotated,
            raw_frame=raw_frame,
            detections=detections,
            fps=self._fps,
            total_counted=self.line_counter.total_count,
            in_counted=self.line_counter.in_count,
            out_counted=self.line_counter.out_count,
            active_in_roi=self.parking_analyzer.active_vehicle_count,
            is_parking_violation=self.parking_analyzer.is_violating,
            new_crossing_events=new_crossings,
            new_violation_events=new_violations,
            new_plates=new_plates,
            new_trap_events=trap_events,
        )

