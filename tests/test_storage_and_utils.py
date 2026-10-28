"""Unit tests for AutoGuardian Storage and Utility modules."""

import os
import shutil
import unittest
import numpy as np

from src.storage.database import DatabaseManager
from src.storage.evidence import EvidenceManager
from src.storage.recorder import VideoRecorder
from src.storage.exporter import ReportExporter
from src.utils.geometry import (
    calculate_centroid,
    ccw_orientation,
    check_line_intersection,
    get_crossing_direction,
    is_point_in_polygon,
)
from src.utils.drawing import (
    draw_detection_box,
    draw_virtual_line,
    draw_roi_polygon,
    draw_dashboard_stats,
    draw_rec_badge,
)


class TestStorageAndUtils(unittest.TestCase):
    test_dir = "outputs/test_run"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_database_and_export(self):
        db_path = os.path.join(self.test_dir, "test.db")
        db = DatabaseManager(db_path)

        # Test insert event
        ev_id = db.insert_vehicle_event(
            track_id=1,
            class_name="car",
            confidence=0.88,
            direction="IN",
            details="Test event",
        )
        self.assertIsNotNone(ev_id)

        # Test insert violation
        v_id = db.insert_violation(
            track_id=1,
            violation_type="PARKING_TIMEOUT",
            duration_seconds=32.5,
            snapshot_path="test.jpg",
            details="Overstayed in zone",
        )
        self.assertIsNotNone(v_id)

        counts = db.get_total_counts()
        self.assertEqual(counts["total_events"], 1)
        self.assertEqual(counts["total_violations"], 1)

        # Test export
        exporter = ReportExporter(db, default_reports_dir=self.test_dir)
        excel_path = exporter.export_to_excel()
        self.assertIsNotNone(excel_path)
        self.assertTrue(os.path.exists(excel_path))

        csv_path = exporter.export_to_csv()
        self.assertIsNotNone(csv_path)
        self.assertTrue(os.path.exists(csv_path))

    def test_geometry(self):
        # Centroid
        cx, cy = calculate_centroid((100, 100, 200, 200))
        self.assertEqual((cx, cy), (150, 150))

        # Line crossing
        line_p1 = (100, 200)
        line_p2 = (500, 200)
        prev_pt = (250, 150)
        curr_pt = (250, 250)

        self.assertTrue(check_line_intersection(line_p1, line_p2, prev_pt, curr_pt))
        direction = get_crossing_direction(line_p1, line_p2, prev_pt, curr_pt)
        self.assertIn(direction, ["IN", "OUT", "CROSSED"])

        # Point in polygon
        polygon = [(0, 0), (100, 0), (100, 100), (0, 100)]
        self.assertTrue(is_point_in_polygon((50, 50), polygon))
        self.assertFalse(is_point_in_polygon((150, 50), polygon))

    def test_drawing_and_recorder(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        draw_detection_box(frame, (50, 50, 150, 150), track_id=42, class_name="car", confidence=0.92)
        draw_virtual_line(frame, (10, 240), (630, 240), count=5)
        draw_roi_polygon(frame, [(100, 100), (300, 100), (300, 300), (100, 300)], is_violating=True)
        draw_dashboard_stats(frame, fps=30.0, total_count=5, violation_count=1)
        draw_rec_badge(frame, blink_on=True)

        self.assertEqual(frame.shape, (480, 640, 3))

        # Test video recorder
        rec_dir = os.path.join(self.test_dir, "recordings")
        recorder = VideoRecorder(output_dir=rec_dir)
        rec_file = recorder.start((640, 480), fps=25.0, format_ext="mp4")
        self.assertIsNotNone(rec_file)
        self.assertTrue(recorder.is_recording)

        for _ in range(10):
            recorder.write_frame(frame)

        saved = recorder.stop()
        self.assertIsNotNone(saved)
        self.assertFalse(recorder.is_recording)
        self.assertTrue(os.path.exists(saved))


if __name__ == "__main__":
    unittest.main()

