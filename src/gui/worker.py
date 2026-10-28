"""Background Video and AI Processing Worker for AutoGuardian.

Inherits from PyQt5 QThread to process video frames and run YOLO tracking asynchronously,
emitting thread-safe Qt signals to update the UI without causing freeze or lag.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from src.core.engine import AutoGuardianAIEngine, EngineResult
from src.streaming.queue_manager import FrameQueueManager
from src.streaming.video_reader import VideoReader
from src.utils.constants import FRAME_QUEUE_MAX_SIZE


class VideoProcessingWorker(QThread):
    """Background QThread worker running VideoReader and AI Engine."""

    # Qt Signals
    frame_ready = pyqtSignal(QImage, object)  # QImage for display, EngineResult
    fps_updated = pyqtSignal(float)
    stats_updated = pyqtSignal(int, int, int, int)  # total, in, out, violations
    violation_detected = pyqtSignal(dict)
    status_message = pyqtSignal(str)
    stream_ended = pyqtSignal()
    recording_status_changed = pyqtSignal(bool, str)
    plate_recognized = pyqtSignal(dict)
    speed_updated = pyqtSignal(int, float)  # (track_id, speed_kmh)

    def __init__(
        self,
        source: Union[str, int],
        engine: Optional[AutoGuardianAIEngine] = None,
        loop_video: bool = True,
        parent: Optional[Any] = None,
    ) -> None:
        """Initializes the VideoProcessingWorker thread.

        Args:
            source: Video file path, webcam ID (int), or RTSP URL.
            engine: AutoGuardianAIEngine instance.
            loop_video: Whether to loop video file continuously.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.source = source
        self.engine: AutoGuardianAIEngine = engine or AutoGuardianAIEngine()
        self.loop_video: bool = loop_video
        self.queue_manager = FrameQueueManager(maxsize=FRAME_QUEUE_MAX_SIZE)
        self.reader: Optional[VideoReader] = None

        self._is_running: bool = False
        self._is_paused: bool = False

    def run(self) -> None:
        """Main thread loop popping frames from reader and running AI engine."""
        self._is_running = True
        self._is_paused = False

        # Initialize and start VideoReader
        self.reader = VideoReader(
            source=self.source,
            queue_manager=self.queue_manager,
            loop_video=self.loop_video,
            on_status_change=lambda msg: self.status_message.emit(msg),
        )

        if not self.reader.start():
            self.status_message.emit(f"Không thể mở nguồn video: {self.source}")
            self.stream_ended.emit()
            return

        self.status_message.emit(f"Đang phát nguồn: {self.source}")

        # Determine source timing properties
        is_live = getattr(self.reader, "_is_live", False)
        source_fps = self.reader.fps if self.reader and self.reader.fps > 0 else 30.0
        frame_time_step = 1.0 / max(1.0, source_fps)
        video_sim_time: float = 0.0

        # Main processing loop
        while self._is_running:
            if self._is_paused:
                time.sleep(0.05)
                continue

            item = self.queue_manager.pop(timeout=0.1)
            if item is None:
                # If reader stopped and queue is empty, stream has ended
                if self.reader is not None and not self.reader.is_running and self.queue_manager.size() == 0:
                    self.status_message.emit("Luồng video đã kết thúc.")
                    self.stream_ended.emit()
                    break
                continue

            try:
                # Unpack frame and accurate video timestamp from reader packet
                if isinstance(item, tuple) and len(item) == 2:
                    frame, frame_timestamp = item
                else:
                    frame = item
                    frame_timestamp = time.time()

                # Process frame via AI Engine with accurate frame timestamp
                result: EngineResult = self.engine.process_frame(frame, timestamp=frame_timestamp)

                # Convert BGR OpenCV image to QImage for Qt display
                h, w, ch = result.annotated_frame.shape
                bytes_per_line = ch * w
                rgb_frame = cv2.cvtColor(result.annotated_frame, cv2.COLOR_BGR2RGB)
                q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

                # Emit display signals
                self.frame_ready.emit(q_img, result)
                self.fps_updated.emit(result.fps)
                self.stats_updated.emit(
                    result.total_counted,
                    result.in_counted,
                    result.out_counted,
                    len(self.engine.parking_analyzer._triggered_violation_ids),
                )

                # Emit violation notifications
                for vi in result.new_violation_events:
                    self.violation_detected.emit(vi)

                # Emit license plate recognition notifications
                for p in result.new_plates:
                    det_speed = self.engine.speed_trap.get_trap_speed(p.track_id) or self.engine.speed_estimator.get_speed(p.track_id)
                    self.plate_recognized.emit({
                        "track_id": p.track_id,
                        "plate_text": p.plate_text,
                        "confidence": p.confidence,
                        "crop_image": p.crop_image,
                        "timestamp": p.timestamp,
                        "speed_kmh": det_speed,
                    })

                # Emit speed updates for active vehicles (Solution 1: Live table update)
                for det in result.detections:
                    if det.track_id is not None and det.speed_kmh is not None and det.speed_kmh > 0:
                        self.speed_updated.emit(det.track_id, det.speed_kmh)

                for te in (result.new_trap_events or []):
                    self.speed_updated.emit(te["track_id"], te["speed_kmh"])

            except Exception as e:
                print(f"[VideoProcessingWorker] Frame processing error: {e}")
                self.status_message.emit(f"Lỗi xử lý khung hình: {e}")

        # Cleanup when stopping
        self._cleanup()

    def pause(self) -> None:
        """Pauses video reading and processing."""
        self._is_paused = True
        if self.reader:
            self.reader.pause()

    def resume(self) -> None:
        """Resumes video reading and processing."""
        self._is_paused = False
        if self.reader:
            self.reader.resume()

    def stop(self) -> None:
        """Stops the worker thread and releases resources."""
        self._is_running = False
        self._is_paused = False
        if self.reader:
            self.reader.stop()
        self.wait(1500)

    def _cleanup(self) -> None:
        """Internal cleanup called on exit."""
        if self.reader:
            self.reader.stop()
            self.reader = None
        self.queue_manager.clear()

    # Dynamic controls passed to engine
    def set_confidence(self, conf: float) -> None:
        self.engine.set_confidence(conf)

    def set_overlay_option(self, option_name: str, enabled: bool) -> None:
        self.engine.set_overlay_option(option_name, enabled)

    def set_pixels_per_meter(self, ppm: float) -> None:
        self.engine.set_pixels_per_meter(ppm)

    def update_counting_line(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> None:
        self.engine.update_counting_line(p1, p2)

    def update_parking_roi(self, points: List[Tuple[int, int]]) -> None:
        self.engine.update_parking_roi(points)

    def update_speed_trap_line_a(self, p1: Tuple[int, int], p2: Tuple[int, int], lane_key: str = "in") -> None:
        self.engine.update_speed_trap_line_a(p1, p2, lane_key=lane_key)

    def update_speed_trap_line_b(self, p1: Tuple[int, int], p2: Tuple[int, int], lane_key: str = "in") -> None:
        self.engine.update_speed_trap_line_b(p1, p2, lane_key=lane_key)

    def update_speed_trap_distance(self, distance_meters: float, enabled: bool = True, lane_key: str = "in") -> None:
        self.engine.update_speed_trap_distance(distance_meters, enabled, lane_key=lane_key)

    def reset_speed_trap_to_defaults(self, lane_key: Optional[str] = None) -> None:
        self.engine.reset_speed_trap_to_defaults(lane_key=lane_key)

    def reset_counters(self) -> None:
        self.engine.reset_counters()
        self.stats_updated.emit(0, 0, 0, 0)

    def toggle_recording(self) -> bool:
        """Toggles video recording on or off.

        Returns:
            Current recording state (True if recording, False if stopped).
        """
        recorder = self.engine.recorder
        if recorder.is_recording:
            saved_file = recorder.stop()
            msg = f"Đã lưu video ghi hình: {saved_file}" if saved_file else "Đã dừng ghi hình."
            self.recording_status_changed.emit(False, msg)
            return False
        else:
            w, h = self.reader.resolution if self.reader else (1280, 720)
            fps = self.reader.fps if self.reader else 25.0
            filepath = recorder.start((w, h), fps=fps, format_ext="mp4")
            if filepath:
                self.recording_status_changed.emit(True, f"Đang ghi hình vào: {filepath}")
                return True
            else:
                self.recording_status_changed.emit(False, "Lỗi khởi tạo file ghi hình!")
                return False

