"""Unit tests for AutoGuardian Core AI and Analytics Engine."""

import os
import shutil
import time
import unittest
import numpy as np

from src.core.detector import VehicleDetection, YOLOVehicleDetector
from src.core.line_counter import LineCrossingCounter
from src.core.parking_analyzer import ParkingViolationAnalyzer
from src.core.engine import AutoGuardianAIEngine
from src.storage.database import DatabaseManager
from src.storage.evidence import EvidenceManager
from src.storage.recorder import VideoRecorder


class TestCoreEngine(unittest.TestCase):
    test_dir = "outputs/test_core"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_line_crossing_strictly_once(self):
        counter = LineCrossingCounter(p1=(0, 100), p2=(200, 100))

        # Frame 1: Vehicle 1 is above the line at (100, 50)
        det_f1 = [
            VehicleDetection(
                bbox=(80, 40, 120, 60),
                track_id=1,
                class_id=2,
                class_name="car",
                confidence=0.9,
                centroid=(100, 50),
                bottom_center=(100, 60),
            )
        ]
        events_f1 = counter.update(det_f1)
        self.assertEqual(len(events_f1), 0)
        self.assertEqual(counter.total_count, 0)

        # Frame 2: Vehicle 1 moves below the line to (100, 150) -> Crossing occurs!
        det_f2 = [
            VehicleDetection(
                bbox=(80, 140, 120, 160),
                track_id=1,
                class_id=2,
                class_name="car",
                confidence=0.9,
                centroid=(100, 150),
                bottom_center=(100, 160),
            )
        ]
        events_f2 = counter.update(det_f2)
        self.assertEqual(len(events_f2), 1)
        self.assertEqual(counter.total_count, 1)

        # Frame 3: Vehicle 1 keeps moving to (100, 200) -> Must NOT count again!
        det_f3 = [
            VehicleDetection(
                bbox=(80, 190, 120, 210),
                track_id=1,
                class_id=2,
                class_name="car",
                confidence=0.9,
                centroid=(100, 200),
                bottom_center=(100, 210),
            )
        ]
        events_f3 = counter.update(det_f3)
        self.assertEqual(len(events_f3), 0)
        self.assertEqual(counter.total_count, 1)

        # Reset test
        counter.reset()
        self.assertEqual(counter.total_count, 0)

    def test_parking_violation_timing(self):
        polygon = [(0, 0), (100, 0), (100, 100), (0, 100)]
        analyzer = ParkingViolationAnalyzer(
            points=polygon,
            threshold_seconds=2.0,
            displacement_tolerance=10.0,
        )

        t0 = 1000.0
        # Vehicle 5 enters polygon at t0
        det_t0 = [
            VehicleDetection(
                bbox=(40, 40, 60, 60),
                track_id=5,
                class_id=2,
                class_name="car",
                confidence=0.95,
                centroid=(50, 50),
                bottom_center=(50, 60),
            )
        ]
        v_t0 = analyzer.update(det_t0, current_time=t0)
        self.assertEqual(len(v_t0), 0)
        self.assertEqual(analyzer.active_vehicle_count, 1)
        self.assertFalse(analyzer.is_violating)

        # Vehicle 5 stays stationary at t0 + 1.0s (less than threshold 2.0s)
        v_t1 = analyzer.update(det_t0, current_time=t0 + 1.0)
        self.assertEqual(len(v_t1), 0)
        self.assertFalse(analyzer.is_violating)

        # Vehicle 5 stays stationary at t0 + 2.5s (> 2.0s threshold) -> Triggers violation!
        v_t2 = analyzer.update(det_t0, current_time=t0 + 2.5)
        self.assertEqual(len(v_t2), 1)
        self.assertTrue(analyzer.is_violating)
        self.assertEqual(v_t2[0]["track_id"], 5)

        # Subsequent call at t0 + 3.0s does not trigger repeated event
        v_t3 = analyzer.update(det_t0, current_time=t0 + 3.0)
        self.assertEqual(len(v_t3), 0)

    def test_ai_engine_pipeline(self):
        db_path = os.path.join(self.test_dir, "engine_test.db")
        db = DatabaseManager(db_path)
        evidence = EvidenceManager(self.test_dir)
        recorder = VideoRecorder(self.test_dir)

        engine = AutoGuardianAIEngine(
            db_manager=db,
            evidence_manager=evidence,
            video_recorder=recorder,
        )

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine.process_frame(dummy_frame)

        self.assertIsNotNone(result.annotated_frame)
        self.assertEqual(result.annotated_frame.shape, (480, 640, 3))
        self.assertIsInstance(result.fps, float)
        self.assertIsInstance(result.total_counted, int)


if __name__ == "__main__":
    unittest.main()

