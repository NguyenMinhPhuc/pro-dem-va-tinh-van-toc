"""Unit tests for AutoGuardian Streaming module."""

import os
import shutil
import time
import unittest
import cv2
import numpy as np

from src.streaming.queue_manager import FrameQueueManager
from src.streaming.video_reader import VideoReader


class TestStreamingModule(unittest.TestCase):
    test_dir = "outputs/test_streaming"
    test_video_path = "outputs/test_streaming/synthetic_video.mp4"

    @classmethod
    def setUpClass(cls):
        os.makedirs(cls.test_dir, exist_ok=True)
        # Create a small synthetic video with 30 frames
        writer = cv2.VideoWriter(
            cls.test_video_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            30.0,
            (320, 240),
        )
        for i in range(30):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.putText(frame, f"F:{i}", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            writer.write(frame)
        writer.release()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_frame_queue_manager_dropping(self):
        qm = FrameQueueManager(maxsize=3)
        self.assertEqual(qm.size(), 0)
        self.assertEqual(qm.dropped_frames, 0)

        # Push 5 frames into queue of size 3
        for i in range(5):
            frame = np.zeros((10, 10, 3), dtype=np.uint8) + i
            qm.push(frame)

        self.assertEqual(qm.size(), 3)
        self.assertEqual(qm.dropped_frames, 2)

        # Pop 1 frame
        popped = qm.pop(timeout=0.1)
        self.assertIsNotNone(popped)
        self.assertEqual(qm.size(), 2)

        # Clear queue
        qm.clear()
        self.assertEqual(qm.size(), 0)

    def test_video_reader_playback(self):
        qm = FrameQueueManager(maxsize=5)
        reader = VideoReader(
            source=self.test_video_path,
            queue_manager=qm,
            loop_video=False,
        )

        started = reader.start()
        self.assertTrue(started)
        self.assertTrue(reader.is_running)
        self.assertEqual(reader.resolution, (320, 240))

        # Wait a short duration to let reader buffer frames
        time.sleep(0.3)
        self.assertGreater(qm.size(), 0)

        # Pop frames
        popped = qm.pop(timeout=0.5)
        self.assertIsNotNone(popped)
        frame = popped[0] if isinstance(popped, tuple) else popped
        self.assertEqual(frame.shape, (240, 320, 3))

        # Pause and resume
        reader.pause()
        self.assertTrue(reader.is_paused)
        reader.resume()
        self.assertFalse(reader.is_paused)

        # Stop
        reader.stop()
        self.assertFalse(reader.is_running)

    def test_video_reader_continuous_loop(self):
        qm = FrameQueueManager(maxsize=10)
        status_logs = []
        reader = VideoReader(
            source=self.test_video_path,
            queue_manager=qm,
            loop_video=True,
            on_status_change=lambda msg: status_logs.append(msg),
        )

        started = reader.start()
        self.assertTrue(started)
        self.assertTrue(reader.loop_video)

        # Allow video to read through frames
        time.sleep(1.2)

        # Reader should still be actively running because loop_video=True
        self.assertTrue(reader.is_running)
        self.assertGreater(qm.size(), 0)

        reader.stop()
        self.assertFalse(reader.is_running)


if __name__ == "__main__":
    unittest.main()

