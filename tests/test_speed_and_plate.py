"""Unit tests for Speed Estimation and License Plate Recognition modules."""

import os
import shutil
import unittest
import cv2
import numpy as np

from src.core.speed_estimator import SpeedEstimator
from src.core.speed_trap import DualLaneSpeedTrap, SpeedTrapZone
from src.core.detector import VehicleDetection
from src.core.plate_recognizer import LicensePlateRecognizer
from src.storage.database import DatabaseManager


class TestSpeedAndPlate(unittest.TestCase):
    test_dir = "outputs/test_speed_plate"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_speed_estimator(self):
        # 25 pixels = 1 meter
        estimator = SpeedEstimator(pixels_per_meter=25.0, min_history_points=3)

        t0 = 100.0
        # Stationary vehicle: same position
        estimator.update(track_id=1, centroid=(100, 100), timestamp=t0)
        estimator.update(track_id=1, centroid=(101, 100), timestamp=t0 + 0.1)
        speed_stationary = estimator.update(track_id=1, centroid=(100, 101), timestamp=t0 + 0.2)
        self.assertIsNotNone(speed_stationary)
        self.assertEqual(speed_stationary, 0.0)

        # Moving vehicle: moves 50 pixels in 0.2 seconds = 2 meters in 0.2s = 10 m/s = 36 km/h
        t_move = 200.0
        estimator.update(track_id=2, centroid=(100, 100), timestamp=t_move)
        estimator.update(track_id=2, centroid=(125, 100), timestamp=t_move + 0.1)
        speed_moving = estimator.update(track_id=2, centroid=(150, 100), timestamp=t_move + 0.2)
        self.assertIsNotNone(speed_moving)
        self.assertGreater(speed_moving, 20.0)
        self.assertLess(speed_moving, 60.0)

    def test_plate_recognizer_reads_real_plate(self):
        recognizer = LicensePlateRecognizer(min_bbox_width=50, enabled=True)
        if not recognizer.enabled:
            self.skipTest(f"Plate models unavailable: {recognizer.load_error}")

        # Real vehicle crop (UK plate "EF10 DZT") filling the whole frame
        car = cv2.imread(os.path.join(os.path.dirname(__file__), "fixtures", "uk_car_EF10DZT.jpg"))
        self.assertIsNotNone(car)
        bbox = (0, 0, car.shape[1], car.shape[0])

        self.assertFalse(recognizer.is_recognized(track_id=10))
        results = []
        for _ in range(recognizer.max_attempts * recognizer.attempt_interval_frames):
            results.extend(recognizer.update(car, [(10, bbox)]))
            if results:
                break

        self.assertEqual(len(results), 1)
        plate_res = results[0]
        self.assertEqual(plate_res.track_id, 10)
        self.assertEqual(plate_res.plate_text, "EF10DZT")
        self.assertGreaterEqual(plate_res.confidence, recognizer.min_confidence)
        self.assertIsNotNone(plate_res.crop_image)

        # Finalized plate is cached and never reported twice
        self.assertTrue(recognizer.is_recognized(track_id=10))
        self.assertEqual(recognizer.update(car, [(10, bbox)]), [])
        self.assertEqual(recognizer.get_plate(10).plate_text, "EF10DZT")

    def test_plate_recognizer_rejects_frame_without_plate(self):
        recognizer = LicensePlateRecognizer(min_bbox_width=50, enabled=True)
        if not recognizer.enabled:
            self.skipTest(f"Plate models unavailable: {recognizer.load_error}")

        # Blank vehicle region: no plate must be invented
        dummy_frame = np.full((300, 300, 3), 90, dtype=np.uint8)
        bbox = (50, 50, 250, 250)
        results = []
        for _ in range(recognizer.max_attempts * recognizer.attempt_interval_frames + 1):
            results.extend(recognizer.update(dummy_frame, [(11, bbox)]))
        self.assertEqual(results, [])
        self.assertFalse(recognizer.is_recognized(track_id=11))

    def test_plate_recognizer_missing_models_disables(self):
        recognizer = LicensePlateRecognizer(detector_model_path="models/plates/missing.onnx")
        self.assertFalse(recognizer.enabled)
        self.assertIsNotNone(recognizer.load_error)
        self.assertEqual(recognizer.update(np.zeros((300, 300, 3), np.uint8), [(1, (0, 0, 300, 300))]), [])

    def test_database_plate_and_speed_migration(self):
        db_path = os.path.join(self.test_dir, "migrated.db")
        db = DatabaseManager(db_path)

        ev_id = db.insert_vehicle_event(
            track_id=10,
            class_name="car",
            confidence=0.92,
            direction="IN",
            license_plate="29A-123.45",
            speed_kmh=42.5,
            details="Gate pass",
        )
        self.assertIsNotNone(ev_id)

        events = db.get_all_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["license_plate"], "29A-123.45")
        self.assertEqual(events[0]["speed_kmh"], 42.5)

    def test_speed_trap_zone(self):
        # Line A at y=100, Line B at y=300, distance=20m
        trap = SpeedTrapZone(
            line_a=((50, 100), (500, 100)),
            line_b=((50, 300), (500, 300)),
            distance_meters=20.0,
            enabled=True,
        )

        # Frame 1: Vehicle above Line A (y=80)
        det1 = VehicleDetection(
            bbox=(100, 60, 140, 100),
            confidence=0.9,
            class_id=2,
            class_name="car",
            track_id=5,
            centroid=(120, 80),
            bottom_center=(120, 100),
        )
        evs1 = trap.update([det1], current_time=0.0)
        self.assertEqual(len(evs1), 0)
        self.assertFalse(trap.is_in_transit(5))

        # Frame 2: Vehicle crosses Line A (centroid moves to y=120) at t=1.0s
        det2 = VehicleDetection(
            bbox=(100, 100, 140, 140),
            confidence=0.9,
            class_id=2,
            class_name="car",
            track_id=5,
            centroid=(120, 120),
            bottom_center=(120, 140),
        )
        evs2 = trap.update([det2], current_time=1.0)
        self.assertEqual(len(evs2), 0)
        self.assertTrue(trap.is_in_transit(5))

        # Frame 3: Vehicle in between lines (y=200) at t=1.5s
        det3 = VehicleDetection(
            bbox=(100, 180, 140, 220),
            confidence=0.9,
            class_id=2,
            class_name="car",
            track_id=5,
            centroid=(120, 200),
            bottom_center=(120, 220),
        )
        evs3 = trap.update([det3], current_time=1.5)
        self.assertEqual(len(evs3), 0)
        self.assertTrue(trap.is_in_transit(5))

        # Frame 4: Vehicle crosses Line B (centroid moves to y=320) at t=2.0s
        # delta_t = 2.0 - 1.0 = 1.0s. Speed = (20m / 1.0s) * 3.6 = 72.0 km/h
        det4 = VehicleDetection(
            bbox=(100, 300, 140, 340),
            confidence=0.9,
            class_id=2,
            class_name="car",
            track_id=5,
            centroid=(120, 320),
            bottom_center=(120, 340),
        )
        evs4 = trap.update([det4], current_time=2.0)
        self.assertEqual(len(evs4), 1)
        self.assertFalse(trap.is_in_transit(5))

        event = evs4[0]
        self.assertEqual(event["track_id"], 5)
        self.assertEqual(event["speed_kmh"], 72.0)
        self.assertEqual(event["distance_meters"], 20.0)
        self.assertEqual(event["transit_time_seconds"], 1.0)
        self.assertEqual(trap.get_trap_speed(5), 72.0)

    def test_dual_lane_speed_trap(self):
        # Default initialization without arguments should populate default coordinates for both lanes
        dual_trap = DualLaneSpeedTrap(enabled=True)
        self.assertIsNotNone(dual_trap.lane_in)
        self.assertIsNotNone(dual_trap.lane_out)
        self.assertEqual(dual_trap.lane_in.distance_meters, 25.0)
        self.assertEqual(dual_trap.lane_out.distance_meters, 25.0)

        # Vehicle 1 enters Lane IN (A at y=250, B at y=750, D=25.0m)
        # Frame 1: y=200 at t=0s
        v1_f1 = VehicleDetection(bbox=(200, 180, 240, 220), confidence=0.9, class_id=2, class_name="car", track_id=1, centroid=(220, 200), bottom_center=(220, 220))
        dual_trap.update([v1_f1], current_time=0.0)

        # Frame 2: y=280 at t=1.0s (crosses Line A)
        v1_f2 = VehicleDetection(bbox=(200, 260, 240, 300), confidence=0.9, class_id=2, class_name="car", track_id=1, centroid=(220, 280), bottom_center=(220, 300))
        dual_trap.update([v1_f2], current_time=1.0)

        # Frame 3: y=780 at t=2.0s (crosses Line B)
        v1_f3 = VehicleDetection(bbox=(200, 760, 240, 800), confidence=0.9, class_id=2, class_name="car", track_id=1, centroid=(220, 780), bottom_center=(220, 800))
        evs = dual_trap.update([v1_f3], current_time=2.0)

        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["lane"], "IN")
        self.assertEqual(evs[0]["speed_kmh"], 90.0)
        self.assertEqual(dual_trap.get_trap_speed(1), 90.0)

        # Test reset to defaults
        dual_trap.lane_in.update_lines(distance_meters=99.0)
        self.assertEqual(dual_trap.lane_in.distance_meters, 99.0)
        dual_trap.reset_to_defaults()
        self.assertEqual(dual_trap.lane_in.distance_meters, 25.0)


if __name__ == "__main__":
    unittest.main()
