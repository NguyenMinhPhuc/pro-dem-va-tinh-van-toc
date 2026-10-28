"""YOLOv8 Vehicle Detector and Tracker for AutoGuardian.

Integrates Ultralytics YOLOv8 with ByteTrack for high-performance,
real-time vehicle detection and persistent track ID assignment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from ultralytics import YOLO

from src.utils.constants import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    MODEL_INPUT_HEIGHT,
    MODEL_INPUT_WIDTH,
)
from src.utils.geometry import calculate_bottom_center, calculate_centroid


@dataclass
class VehicleDetection:
    """Represents a single detected and tracked vehicle in a video frame."""

    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    track_id: Optional[int]
    class_id: int
    class_name: str
    confidence: float
    centroid: Tuple[int, int]
    bottom_center: Tuple[int, int]
    speed_kmh: Optional[float] = None
    license_plate: Optional[str] = None


class YOLOVehicleDetector:
    """Encapsulates YOLOv8 vehicle detection and ByteTrack tracking."""

    # Default COCO classes for vehicles: 2=car, 3=motorcycle, 5=bus, 7=truck
    DEFAULT_VEHICLE_CLASSES: Dict[int, str] = {
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck",
    }

    def __init__(
        self,
        model_path: str = "models/yolov8n.pt",
        target_classes: Optional[List[int]] = None,
        device: str = "cpu",
    ) -> None:
        """Initializes the YOLO vehicle detector.

        Args:
            model_path: Path to YOLO weights (.pt file).
            target_classes: List of class IDs to filter. Defaults to vehicle classes.
            device: 'cpu' or 'cuda' or '0'.
        """
        self.model_path = Path(model_path)
        self.target_classes = target_classes or list(self.DEFAULT_VEHICLE_CLASSES.keys())
        self.device = device

        if not self.model_path.exists():
            # If specified model doesn't exist, fallback to yolov8n.pt in current dir or download
            print(f"[YOLOVehicleDetector] Warning: {self.model_path} not found. Loading 'yolov8n.pt'...")
            self.model = YOLO("yolov8n.pt")
        else:
            self.model = YOLO(str(self.model_path))

    def detect_and_track(
        self,
        frame: np.ndarray,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        tracker_type: str = "bytetrack.yaml",
    ) -> List[VehicleDetection]:
        """Runs inference and tracking on a video frame.

        Args:
            frame: OpenCV BGR frame.
            confidence_threshold: Minimum confidence score to accept detection.
            tracker_type: Tracking configuration ('bytetrack.yaml' or 'botsort.yaml').

        Returns:
            List of VehicleDetection dataclass objects.
        """
        if frame is None or frame.size == 0:
            return []

        try:
            # Ultralytics track maintains internal state when persist=True
            results = self.model.track(
                source=frame,
                persist=True,
                tracker=tracker_type,
                classes=self.target_classes,
                conf=float(confidence_threshold),
                imgsz=(MODEL_INPUT_WIDTH, MODEL_INPUT_HEIGHT),
                verbose=False,
                device=self.device,
            )

            detections: List[VehicleDetection] = []
            if not results or len(results) == 0:
                return detections

            result = results[0]
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                return detections

            # Extract coordinates, classes, confidences, and tracking IDs
            xyxy_list = boxes.xyxy.cpu().numpy().astype(int)
            conf_list = boxes.conf.cpu().numpy().astype(float)
            cls_list = boxes.cls.cpu().numpy().astype(int)

            # Track IDs may be None if tracker hasn't assigned an ID yet
            track_ids = (
                boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(xyxy_list)
            )

            for bbox_arr, conf, cls_id, t_id in zip(xyxy_list, conf_list, cls_list, track_ids):
                bbox = (int(bbox_arr[0]), int(bbox_arr[1]), int(bbox_arr[2]), int(bbox_arr[3]))
                class_name = self.DEFAULT_VEHICLE_CLASSES.get(int(cls_id), f"class_{cls_id}")
                centroid = calculate_centroid(bbox)
                bottom_center = calculate_bottom_center(bbox)

                det = VehicleDetection(
                    bbox=bbox,
                    track_id=int(t_id) if t_id is not None else None,
                    class_id=int(cls_id),
                    class_name=class_name,
                    confidence=float(conf),
                    centroid=centroid,
                    bottom_center=bottom_center,
                )
                detections.append(det)

            return detections
        except Exception as e:
            print(f"[YOLOVehicleDetector] Inference error: {e}")
            return []

