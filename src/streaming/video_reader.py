"""Multi-Source Video Reader for AutoGuardian.

Supports File video, Webcam, and RTSP IP Camera streams with automatic
reconnection and decoupled frame reading via background worker thread.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Optional, Tuple, Union
import cv2
import numpy as np

from src.streaming.queue_manager import FrameQueueManager
from src.utils.constants import FRAME_QUEUE_MAX_SIZE, RTSP_RECONNECT_INTERVAL_SECONDS


class VideoReader:
    """Reads video frames from diverse sources (File, Webcam, RTSP) into a FrameQueueManager."""

    def __init__(
        self,
        source: Union[str, int],
        queue_manager: Optional[FrameQueueManager] = None,
        loop_video: bool = True,
        reconnect_interval: float = RTSP_RECONNECT_INTERVAL_SECONDS,
        on_status_change: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initializes the VideoReader.

        Args:
            source: Path to video file, Webcam index (int), or RTSP URL string.
            queue_manager: Optional FrameQueueManager. If None, creates a default one.
            loop_video: If True, loops file video on reaching EOF.
            reconnect_interval: Seconds between RTSP reconnection attempts.
            on_status_change: Callback invoked with status message strings.
        """
        self.source = source
        self.queue: FrameQueueManager = queue_manager or FrameQueueManager(maxsize=FRAME_QUEUE_MAX_SIZE)
        self.loop_video = loop_video
        self.reconnect_interval = reconnect_interval
        self.on_status_change = on_status_change

        self._is_rtsp: bool = isinstance(source, str) and source.lower().startswith("rtsp://")
        self._is_live: bool = isinstance(source, int) or self._is_rtsp

        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        self._fps: float = 30.0
        self._width: int = 1280
        self._height: int = 720
        self._total_frames: int = 0
        self._is_connected: bool = False
        self._loop_offset: float = 0.0
        self._lock = threading.Lock()

    @property
    def fps(self) -> float:
        """Returns detected frame rate of the source."""
        return self._fps

    @property
    def resolution(self) -> Tuple[int, int]:
        """Returns (width, height) resolution of the source."""
        return self._width, self._height

    @property
    def is_connected(self) -> bool:
        """Returns connection status."""
        return self._is_connected

    @property
    def is_running(self) -> bool:
        """Returns True if reading thread is active."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_paused(self) -> bool:
        """Returns True if stream reading is paused."""
        return self._pause_event.is_set()

    def _notify(self, message: str) -> None:
        """Invokes the status callback if defined."""
        if self.on_status_change is not None:
            try:
                self.on_status_change(message)
            except Exception as e:
                print(f"[VideoReader] Status callback error: {e}")

    def _open_capture(self) -> bool:
        """Opens or reopens the video capture device."""
        try:
            if self._cap is not None:
                self._cap.release()

            if isinstance(self.source, int):
                # Webcam: use DirectShow backend on Windows for fast opening
                self._cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
                if not self._cap.isOpened():
                    self._cap = cv2.VideoCapture(self.source)
            else:
                self._cap = cv2.VideoCapture(str(self.source))

            if self._cap.isOpened():
                detected_fps = self._cap.get(cv2.CAP_PROP_FPS)
                self._fps = detected_fps if detected_fps > 0 else 30.0
                self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
                self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
                self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self._is_connected = True
                self._notify(f"Ket noi nguon thanh cong: {self.source} ({self._width}x{self._height} @ {self._fps:.1f} FPS)")
                return True
            else:
                self._is_connected = False
                self._notify(f"Khong the mo nguon: {self.source}")
                return False
        except (cv2.error, OSError) as e:
            self._is_connected = False
            self._notify(f"Loi mo nguon: {e}")
            return False

    def start(self) -> bool:
        """Starts the background reading thread.

        Returns:
            True if started successfully, False otherwise.
        """
        if self.is_running:
            return True

        self._stop_event.clear()
        self._pause_event.clear()

        # Initial open attempt
        if not self._open_capture() and not self._is_rtsp:
            return False

        self._thread = threading.Thread(target=self._read_loop, daemon=True, name="VideoReaderThread")
        self._thread.start()
        return True

    def pause(self) -> None:
        """Pauses frame reading."""
        self._pause_event.set()
        self._notify("Tam dung luong video")

    def resume(self) -> None:
        """Resumes paused frame reading."""
        self._pause_event.clear()
        self._notify("Tiep tuc phat luong video")

    def stop(self) -> None:
        """Stops reading frames and releases all video capture resources."""
        self._stop_event.set()
        self._pause_event.clear()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

        with self._lock:
            try:
                if self._cap is not None:
                    self._cap.release()
                    self._cap = None
            except cv2.error as e:
                print(f"[VideoReader] Error releasing capture: {e}")
            finally:
                self._is_connected = False
                self.queue.clear()
                self._notify("Da dung luong video va giai phong bo nho")

    def _read_loop(self) -> None:
        """Background thread loop for continuous frame acquisition."""
        frame_delay = 1.0 / max(1.0, self._fps)

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.05)
                continue

            # Handle reconnection for RTSP
            if self._cap is None or not self._cap.isOpened():
                if self._is_rtsp:
                    self._notify(f"Mat ket noi RTSP. Thu lai sau {self.reconnect_interval:.0f}s...")
                    time.sleep(self.reconnect_interval)
                    self._open_capture()
                    continue
                else:
                    break

            start_time = time.perf_counter()
            try:
                ret, frame = self._cap.read()
            except cv2.error as e:
                print(f"[VideoReader] Read error: {e}")
                ret = False
                frame = None

            if not ret or frame is None:
                if self._is_live:
                    self._is_connected = False
                    self._notify("Mat tin hieu video live. Dang thu ket noi lai...")
                    time.sleep(self.reconnect_interval)
                    self._open_capture()
                    continue
                else:
                    # Video file reached EOF
                    if self.loop_video:
                        dur = self._total_frames / max(1.0, self._fps) if self._total_frames > 0 else 0.0
                        self._loop_offset += dur
                        # Try seeking to beginning first
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self._cap.read()
                        if not ret or frame is None:
                            # If seeking fails (container index issue), reopen capture
                            self._open_capture()
                            ret, frame = self._cap.read() if self._cap else (False, None)

                        if ret and frame is not None:
                            self._notify("Video đã phát hết, tự động phát lặp lại từ đầu...")
                            self.queue.push((frame, self._loop_offset))
                            continue
                        else:
                            self._notify("Không thể tự động lặp lại video.")
                            break
                    else:
                        self._notify("Ket thuc file video (EOF)")
                        break

            # Compute precise frame timestamp for accurate speed calculation
            if self._is_live:
                current_ts = time.time()
            else:
                pos_msec = self._cap.get(cv2.CAP_PROP_POS_MSEC) if self._cap else 0.0
                if pos_msec and pos_msec > 0:
                    current_ts = self._loop_offset + (pos_msec / 1000.0)
                else:
                    frame_idx = self._cap.get(cv2.CAP_PROP_POS_FRAMES) if self._cap else 0.0
                    current_ts = self._loop_offset + (frame_idx / max(1.0, self._fps))

            # Push frame and exact timestamp packet to queue
            self.queue.push((frame, current_ts))

            # For video files, control playback timing to match real FPS
            if not self._is_live:
                elapsed = time.perf_counter() - start_time
                sleep_time = frame_delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        # Finished loop
        self._is_connected = False

