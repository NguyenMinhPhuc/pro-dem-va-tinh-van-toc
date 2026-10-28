"""Video Recorder for AutoGuardian.

Records processed frames with overlays to MP4 or AVI video files using cv2.VideoWriter.
Ensures clean resource release and error handling.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np


class VideoRecorder:
    """Handles recording processed output video frames to disk."""

    def __init__(self, output_dir: str = "outputs/recordings") -> None:
        """Initializes the VideoRecorder.

        Args:
            output_dir: Directory where video recordings are stored.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._writer: Optional[cv2.VideoWriter] = None
        self._is_recording: bool = False
        self._current_path: Optional[str] = None
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        """Returns True if recording is currently active."""
        return self._is_recording

    @property
    def current_file_path(self) -> Optional[str]:
        """Returns the file path of current recording."""
        return self._current_path

    def start(self, frame_size: Tuple[int, int], fps: float = 25.0, format_ext: str = "mp4") -> Optional[str]:
        """Starts a new video recording session.

        Args:
            frame_size: (width, height) of frames to be recorded.
            fps: Frame rate of the recording.
            format_ext: Extension, either 'mp4' or 'avi'.

        Returns:
            The output file path string if successful, None otherwise.
        """
        with self._lock:
            if self._is_recording:
                self.stop()

            try:
                width, height = frame_size
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"RECORD_{timestamp_str}.{format_ext}"
                output_file = self.output_dir / filename

                if format_ext.lower() == "mp4":
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                else:
                    fourcc = cv2.VideoWriter_fourcc(*"XVID")

                self._writer = cv2.VideoWriter(
                    str(output_file),
                    fourcc,
                    max(1.0, float(fps)),
                    (int(width), int(height)),
                )

                if not self._writer.isOpened():
                    print(f"[VideoRecorder] Failed to open VideoWriter for {output_file}")
                    self._writer = None
                    self._is_recording = False
                    return None

                self._is_recording = True
                self._current_path = str(output_file).replace("\\", "/")
                return self._current_path
            except (cv2.error, OSError) as e:
                print(f"[VideoRecorder] Error starting recording: {e}")
                self._writer = None
                self._is_recording = False
                return None

    def write_frame(self, frame: np.ndarray) -> bool:
        """Writes a single video frame to the recording.

        Args:
            frame: BGR image frame.

        Returns:
            True if written successfully, False otherwise.
        """
        with self._lock:
            if not self._is_recording or self._writer is None:
                return False

            try:
                self._writer.write(frame)
                return True
            except cv2.error as e:
                print(f"[VideoRecorder] Error writing frame: {e}")
                return False

    def stop(self) -> Optional[str]:
        """Stops the recording session and flushes the video file to disk.

        Returns:
            The saved file path or None.
        """
        with self._lock:
            if not self._is_recording:
                return None

            saved_path = self._current_path
            try:
                if self._writer is not None:
                    self._writer.release()
                    self._writer = None
            except cv2.error as e:
                print(f"[VideoRecorder] Error releasing writer: {e}")
            finally:
                self._is_recording = False
                self._current_path = None

            return saved_path

