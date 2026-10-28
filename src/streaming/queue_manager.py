"""Frame Queue Manager for AutoGuardian.

Maintains a low-latency FIFO/Drop-oldest queue to eliminate latency
and prevent memory leaks during real-time video processing.
"""

from __future__ import annotations

import queue
import threading
from typing import Optional
import numpy as np


class FrameQueueManager:
    """Thread-safe queue manager with automatic frame dropping for real-time streaming."""

    def __init__(self, maxsize: int = 3) -> None:
        """Initializes the FrameQueueManager.

        Args:
            maxsize: Maximum number of frames held in queue.
        """
        self.maxsize = max(1, maxsize)
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=self.maxsize)
        self._lock = threading.Lock()
        self._dropped_frames_count: int = 0

    @property
    def dropped_frames(self) -> int:
        """Returns the total number of frames dropped due to queue congestion."""
        with self._lock:
            return self._dropped_frames_count

    def push(self, frame: np.ndarray) -> bool:
        """Pushes a new frame into the queue.

        If the queue is full, drops the oldest frame to preserve real-time low latency.

        Args:
            frame: OpenCV BGR image frame.

        Returns:
            True if frame was enqueued.
        """
        with self._lock:
            if self._queue.full():
                try:
                    # Drop oldest frame
                    _ = self._queue.get_nowait()
                    self._dropped_frames_count += 1
                except queue.Empty:
                    pass

            try:
                self._queue.put_nowait(frame)
                return True
            except queue.Full:
                return False

    def pop(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        """Retrieves the next frame from the queue.

        Args:
            timeout: Maximum seconds to wait for a frame.

        Returns:
            OpenCV BGR frame or None if timed out.
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear(self) -> None:
        """Clears all buffered frames in queue."""
        with self._lock:
            while not self._queue.empty():
                try:
                    _ = self._queue.get_nowait()
                except queue.Empty:
                    break

    def size(self) -> int:
        """Returns current number of buffered frames."""
        return self._queue.qsize()

