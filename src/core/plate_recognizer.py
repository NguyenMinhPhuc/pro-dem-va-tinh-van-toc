"""Automatic License Plate Recognition (ANPR/ALPR) Module for AutoGuardian.

Two-stage pipeline running on ONNX Runtime (works on CPU-only machines):
  1. Plate localisation inside each vehicle crop with a YOLOv9 plate detector
     (`open-image-models`).
  2. Character recognition with a multi-country plate OCR model (`fast-plate-ocr`,
     65 regions incl. Vietnam, UK, EU, US) returning per-character confidences.

Each vehicle is read over several frames while it approaches the camera; readings
are voted by confidence and only a reliable result is published (no fake plates).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple
import cv2
import numpy as np

DEFAULT_DETECTOR_MODEL = "models/plates/yolo-v9-t-384-license-plates-end2end.onnx"
DEFAULT_OCR_MODEL = "models/plates/cct_s_v2_global.onnx"
DEFAULT_OCR_CONFIG = "models/plates/cct_s_v2_global_plate_config.yaml"


@dataclass
class PlateResult:
    """Represents a recognized vehicle license plate."""

    track_id: int
    plate_text: str
    confidence: float
    crop_image: np.ndarray
    timestamp: str
    region: Optional[str] = None


@dataclass
class _PlateReading:
    """Accumulated OCR votes for one candidate text of a vehicle."""

    votes: int = 0
    best_confidence: float = 0.0
    best_crop: Optional[np.ndarray] = None
    region: Optional[str] = None


@dataclass
class _TrackState:
    """Per-vehicle recognition progress."""

    attempts: int = 0
    last_attempt_frame: int = -(10**9)
    last_seen_frame: int = 0
    readings: Dict[str, _PlateReading] = field(default_factory=dict)


class LicensePlateRecognizer:
    """Locates and reads license plates of tracked vehicles using ONNX models."""

    def __init__(
        self,
        min_bbox_width: int = 90,
        enabled: bool = True,
        detector_model_path: str = DEFAULT_DETECTOR_MODEL,
        ocr_model_path: str = DEFAULT_OCR_MODEL,
        ocr_config_path: str = DEFAULT_OCR_CONFIG,
        min_confidence: float = 0.9,
        high_confidence: float = 0.95,
        min_char_confidence: float = 0.45,
        min_plate_length: int = 5,
        attempt_interval_frames: int = 3,
        max_attempts: int = 12,
        max_reads_per_frame: int = 2,
        lost_track_frames: int = 15,
    ) -> None:
        """Initializes the LicensePlateRecognizer.

        Args:
            min_bbox_width: Minimum vehicle box width required before attempting a read.
            enabled: Whether license plate recognition is active.
            detector_model_path: ONNX plate detector (YOLOv9, open-image-models).
            ocr_model_path: ONNX plate OCR model (fast-plate-ocr).
            ocr_config_path: YAML plate config matching the OCR model.
            min_confidence: Minimum mean character confidence for a plate to be accepted.
            high_confidence: Mean confidence at which a single reading is accepted immediately.
            min_char_confidence: Readings with any character below this are discarded.
            min_plate_length: Readings shorter than this (partial plates) are discarded.
            attempt_interval_frames: Frames to wait between two reads of the same vehicle.
            max_attempts: Reads per vehicle before settling on the best candidate.
            max_reads_per_frame: OCR budget per frame to keep the pipeline real-time on CPU.
            lost_track_frames: Frames without a vehicle before its pending readings are settled.
        """
        self.min_bbox_width = min_bbox_width
        self.min_confidence = min_confidence
        self.high_confidence = high_confidence
        self.min_char_confidence = min_char_confidence
        self.min_plate_length = min_plate_length
        self.attempt_interval_frames = attempt_interval_frames
        self.max_attempts = max_attempts
        self.max_reads_per_frame = max_reads_per_frame
        self.lost_track_frames = lost_track_frames

        # Finalized results: track_id -> PlateResult (published exactly once per vehicle)
        self._cache: Dict[int, PlateResult] = {}
        self._states: Dict[int, _TrackState] = {}
        self._given_up: set[int] = set()
        self._frame_idx: int = 0

        self._detector = None
        self._ocr = None
        self.load_error: Optional[str] = None
        self.enabled = enabled and self._load_models(detector_model_path, ocr_model_path, ocr_config_path)

    def _load_models(self, detector_model_path: str, ocr_model_path: str, ocr_config_path: str) -> bool:
        """Loads ONNX models. Returns False (recognition disabled) if they are unavailable."""
        try:
            import onnxruntime as ort
            from fast_plate_ocr import LicensePlateRecognizer as FastPlateOCR
            from open_image_models import create_detector

            for path in (detector_model_path, ocr_model_path, ocr_config_path):
                if not os.path.isfile(path):
                    raise FileNotFoundError(f"Missing plate model file: {path}")

            providers = ["CPUExecutionProvider"]
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers.insert(0, "CUDAExecutionProvider")

            # Small models: few threads and no busy-wait spinning, so ONNX Runtime does not
            # steal CPU from the YOLO vehicle detector on CPU-only machines.
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = max(1, min(4, (os.cpu_count() or 2) // 2))
            sess_options.inter_op_num_threads = 1
            sess_options.add_session_config_entry("session.intra_op.allow_spinning", "0")

            self._detector = create_detector(
                detector_model_path,
                backend="yolo_v9",
                class_labels=("License Plate",),
                conf_thresh=0.3,
                providers=providers,
                sess_options=sess_options,
            )
            self._ocr = FastPlateOCR(
                onnx_model_path=ocr_model_path,
                plate_config_path=ocr_config_path,
                providers=providers,
                sess_options=sess_options,
            )
            return True
        except Exception as e:
            self.load_error = str(e)
            print(f"[LicensePlateRecognizer] Plate recognition disabled: {e}")
            return False

    def is_recognized(self, track_id: int) -> bool:
        """Returns True if the vehicle already has a recognized plate."""
        return track_id in self._cache

    def get_plate(self, track_id: int) -> Optional[PlateResult]:
        """Returns cached plate result for a vehicle."""
        return self._cache.get(track_id)

    def update(
        self,
        frame: np.ndarray,
        vehicles: Sequence[Tuple[int, Tuple[int, int, int, int]]],
    ) -> List[PlateResult]:
        """Processes all tracked vehicles of a frame within the per-frame OCR budget.

        Args:
            frame: Full BGR video frame.
            vehicles: (track_id, bbox) pairs of the current frame.

        Returns:
            Plates finalized during this frame (each vehicle is reported only once).
        """
        if not self.enabled:
            return []

        self._frame_idx += 1
        new_results: List[PlateResult] = []

        for track_id, _ in vehicles:
            self._states.setdefault(track_id, _TrackState()).last_seen_frame = self._frame_idx

        # Largest (closest) vehicles first: their plates are the most legible
        pending = [
            (tid, bbox)
            for tid, bbox in vehicles
            if tid not in self._cache and tid not in self._given_up and self._is_due(tid, bbox)
        ]
        pending.sort(key=lambda v: v[1][2] - v[1][0], reverse=True)

        for track_id, bbox in pending[: self.max_reads_per_frame]:
            result = self.recognize(frame, bbox, track_id)
            if result is not None:
                new_results.append(result)

        new_results.extend(self._settle_lost_tracks())
        return new_results

    def _is_due(self, track_id: int, bbox: Tuple[int, int, int, int]) -> bool:
        x1, y1, x2, y2 = bbox
        if x2 - x1 < self.min_bbox_width or y2 - y1 < 50:
            return False
        state = self._states.get(track_id)
        return state is None or self._frame_idx - state.last_attempt_frame >= self.attempt_interval_frames

    def recognize(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        track_id: int,
    ) -> Optional[PlateResult]:
        """Performs one read attempt for a vehicle and returns the plate once it is reliable.

        Args:
            frame: Full BGR video frame.
            bbox: (x1, y1, x2, y2) of the vehicle.
            track_id: Vehicle track ID.

        Returns:
            PlateResult when the vehicle's plate is (or becomes) finalized, otherwise None.
        """
        if not self.enabled or track_id is None:
            return None

        if track_id in self._cache:
            return self._cache[track_id]

        x1, y1, x2, y2 = bbox
        if x2 - x1 < self.min_bbox_width or y2 - y1 < 50:
            return None

        state = self._states.setdefault(track_id, _TrackState(last_seen_frame=self._frame_idx))
        state.attempts += 1
        state.last_attempt_frame = self._frame_idx

        reading = self._read_plate(frame, bbox)
        if reading is not None:
            text, conf, crop, region = reading
            entry = state.readings.setdefault(text, _PlateReading())
            entry.votes += 1
            if conf > entry.best_confidence:
                entry.best_confidence = conf
                entry.best_crop = crop
                entry.region = region

        best_text, best = self._best_reading(state)
        if best is not None and (
            best.best_confidence >= self.high_confidence
            or (best.votes >= 2 and best.best_confidence >= self.min_confidence)
        ):
            return self._finalize(track_id, best_text, best)

        if state.attempts >= self.max_attempts:
            return self._settle(track_id)
        return None

    def _read_plate(
        self, frame: np.ndarray, bbox: Tuple[int, int, int, int]
    ) -> Optional[Tuple[str, float, np.ndarray, Optional[str]]]:
        """Detects the plate inside the vehicle crop and reads it.

        Returns:
            (text, mean_char_confidence, plate_crop_bgr, region) or None if unreadable.
        """
        x1, y1, x2, y2 = bbox
        pad_x, pad_y = int((x2 - x1) * 0.05), int((y2 - y1) * 0.05)
        vx1, vy1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
        vx2, vy2 = min(frame.shape[1], x2 + pad_x), min(frame.shape[0], y2 + pad_y)
        vehicle_crop = frame[vy1:vy2, vx1:vx2]
        if vehicle_crop.size == 0:
            return None

        try:
            detections = self._detector.predict(vehicle_crop)
            if not detections:
                return None
            plate_box = max(detections, key=lambda d: d.confidence).bounding_box
            px1, py1 = max(0, plate_box.x1), max(0, plate_box.y1)
            px2, py2 = min(vehicle_crop.shape[1], plate_box.x2), min(vehicle_crop.shape[0], plate_box.y2)
            if px2 - px1 < 8 or py2 - py1 < 4:
                return None
            plate_crop = vehicle_crop[py1:py2, px1:px2].copy()

            prediction = self._ocr.run_one(cv2.cvtColor(plate_crop, cv2.COLOR_BGR2RGB), return_confidence=True)
        except Exception as e:
            print(f"[LicensePlateRecognizer] Read error: {e}")
            return None

        text = prediction.plate
        if len(text) < self.min_plate_length or prediction.char_probs is None:
            return None
        char_probs = np.asarray(prediction.char_probs, dtype=float)[: len(text)]
        if float(char_probs.min()) < self.min_char_confidence:
            return None
        return text, float(char_probs.mean()), plate_crop, prediction.region

    @staticmethod
    def _best_reading(state: _TrackState) -> Tuple[Optional[str], Optional[_PlateReading]]:
        if not state.readings:
            return None, None
        # Vote weight: repeated readings dominate, confidence breaks ties
        text = max(state.readings, key=lambda t: state.readings[t].votes * state.readings[t].best_confidence)
        return text, state.readings[text]

    def _settle(self, track_id: int) -> Optional[PlateResult]:
        """Finalizes the best candidate if reliable enough, otherwise gives up on the vehicle."""
        state = self._states.get(track_id)
        best_text, best = self._best_reading(state) if state else (None, None)
        if best is not None and best.best_confidence >= self.min_confidence:
            return self._finalize(track_id, best_text, best)
        self._given_up.add(track_id)
        self._states.pop(track_id, None)
        return None

    def _settle_lost_tracks(self) -> List[PlateResult]:
        """Settles vehicles that left the scene before their plate was finalized."""
        lost = [
            tid
            for tid, st in self._states.items()
            if self._frame_idx - st.last_seen_frame > self.lost_track_frames
        ]
        results: List[PlateResult] = []
        for tid in lost:
            res = self._settle(tid)
            if res is not None:
                results.append(res)
        return results

    def _finalize(self, track_id: int, text: str, reading: _PlateReading) -> PlateResult:
        thumb = reading.best_crop
        h_p, w_p = thumb.shape[:2]
        target_h = 70
        thumb = cv2.resize(thumb, (max(140, int(w_p * target_h / h_p)), target_h), interpolation=cv2.INTER_CUBIC)
        cv2.rectangle(thumb, (0, 0), (thumb.shape[1] - 1, thumb.shape[0] - 1), (0, 255, 0), 2)

        result = PlateResult(
            track_id=track_id,
            plate_text=text,
            confidence=reading.best_confidence,
            crop_image=thumb,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            region=reading.region,
        )
        self._cache[track_id] = result
        self._states.pop(track_id, None)
        return result

    def reset(self) -> None:
        """Clears cached recognized plates and pending readings."""
        self._cache.clear()
        self._states.clear()
        self._given_up.clear()
        self._frame_idx = 0
