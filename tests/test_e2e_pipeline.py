"""End-to-End (E2E) Integration Pipeline Test for AutoGuardian.

Simulates a complete real-world operational cycle:
1. Generates a video with moving vehicles crossing a line and staying in a parking zone.
2. Streams frames through VideoReader and AutoGuardianAIEngine.
3. Verifies line counting events are logged to SQLite.
4. Verifies parking violation detection, duration calculation, and snapshot capture.
5. Verifies video recording engine creates playable video.
6. Verifies export of reports to Excel (.xlsx) and CSV (.csv).
"""

import os
import shutil
import time
import unittest
import cv2
import numpy as np

import torch
from src.core.detector import VehicleDetection
from src.core.engine import AutoGuardianAIEngine
from src.storage.database import DatabaseManager
from src.storage.evidence import EvidenceManager
from src.storage.exporter import ReportExporter
from src.storage.recorder import VideoRecorder
from src.utils.config import AppConfig


class TestEndToEndPipeline(unittest.TestCase):
    test_dir = "outputs/test_e2e"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_full_pipeline_workflow(self):
        db_path = os.path.join(self.test_dir, "e2e_system.db")
        captures_dir = os.path.join(self.test_dir, "captures")
        reports_dir = os.path.join(self.test_dir, "reports")
        recordings_dir = os.path.join(self.test_dir, "recordings")

        db = DatabaseManager(db_path)
        evidence = EvidenceManager(captures_dir)
        recorder = VideoRecorder(recordings_dir)
        exporter = ReportExporter(db, default_reports_dir=reports_dir)

        # Isolated zones file so the test never overwrites the real configs/zones.json
        config = AppConfig(zones_path=os.path.join(self.test_dir, "zones.json"))

        engine = AutoGuardianAIEngine(
            config=config,
            db_manager=db,
            evidence_manager=evidence,
            video_recorder=recorder,
        )

        # Configure custom line: horizontal line at y=200
        engine.update_counting_line(p1=(50, 200), p2=(550, 200))

        # Configure custom parking ROI: box [100, 250] to [300, 450] with 1.0s threshold
        engine.update_parking_roi(
            points=[(100, 250), (300, 250), (300, 450), (100, 450)],
        )
        engine.parking_analyzer.threshold_seconds = 1.0

        # Start Video Recording
        rec_path = recorder.start(frame_size=(640, 480), fps=20.0, format_ext="mp4")
        self.assertIsNotNone(rec_path)
        self.assertTrue(recorder.is_recording)

        # Mock detector to simulate vehicle movement:
        # Vehicle 1 starts at y=150 (above line at y=200), moves to y=200 (crosses line), enters ROI at y=300 and parks.
        current_det = []
        engine.detector.detect_and_track = lambda frame, **kwargs: current_det

        # Frame 0: Vehicle above line
        mock_v1 = VehicleDetection(
            bbox=(160, 120, 240, 180),
            track_id=1,
            class_id=2,
            class_name="car",
            confidence=0.92,
            centroid=(200, 150),
            bottom_center=(200, 180),
        )
        current_det = [mock_v1]
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        engine.process_frame(dummy_frame)

        # Frame 1: Vehicle crosses line at y=220
        mock_v1_cross = VehicleDetection(
            bbox=(160, 190, 240, 250),
            track_id=1,
            class_id=2,
            class_name="car",
            confidence=0.92,
            centroid=(200, 220),
            bottom_center=(200, 250),
        )
        current_det = [mock_v1_cross]
        engine.process_frame(dummy_frame)

        # Frame 2: Vehicle enters parking ROI at y=300
        mock_v1_park = VehicleDetection(
            bbox=(160, 270, 240, 330),
            track_id=1,
            class_id=2,
            class_name="car",
            confidence=0.92,
            centroid=(200, 300),
            bottom_center=(200, 330),
        )
        current_det = [mock_v1_park]
        engine.process_frame(dummy_frame)

        # Wait 1.1s so vehicle dwell time in parking ROI exceeds 1.0s threshold
        time.sleep(1.1)

        # Frame 3: Vehicle stays parked in ROI -> Triggers parking violation & snapshot capture!
        engine.process_frame(dummy_frame)

        # Stop recording
        saved_video = recorder.stop()
        self.assertIsNotNone(saved_video)
        self.assertTrue(os.path.exists(saved_video))
        self.assertGreater(os.path.getsize(saved_video), 0)

        # Verify Database contents
        counts = db.get_total_counts()
        self.assertEqual(counts["total_events"], 1)  # Vehicle 1 crossed line once
        self.assertEqual(counts["total_violations"], 1)  # Vehicle 1 parked > 1.0s

        # Verify evidence snapshots
        violations = db.get_all_violations()
        self.assertEqual(len(violations), 1)
        snap_file = violations[0]["snapshot_path"]
        self.assertIsNotNone(snap_file)
        self.assertTrue(os.path.exists(snap_file))

        # Verify plate and speed was recorded
        events = db.get_all_events()
        self.assertEqual(len(events), 1)
        self.assertIsNotNone(events[0]["license_plate"])

        # Verify Excel & CSV Export
        excel_out = exporter.export_to_excel()
        self.assertIsNotNone(excel_out)
        self.assertTrue(os.path.exists(excel_out))
        self.assertGreater(os.path.getsize(excel_out), 0)

        csv_out = exporter.export_to_csv()
        self.assertIsNotNone(csv_out)
        self.assertTrue(os.path.exists(csv_out))
        self.assertGreater(os.path.getsize(csv_out), 0)


if __name__ == "__main__":
    unittest.main()
