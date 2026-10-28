"""Unit tests for AutoGuardian GUI components."""

import os
import sys
import torch  # Ensure PyTorch DLLs are loaded before Qt
import unittest
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication

from src.gui.canvas import DrawingMode, InteractiveVideoCanvas
from src.gui.dialogs import ROIConfigDialog, RTSPInputDialog, SnapshotViewerDialog
from src.gui.main_window import MainWindow

# Initialize single QApplication instance for tests
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestGUIComponents(unittest.TestCase):
    def test_canvas_drawing_mode(self):
        canvas = InteractiveVideoCanvas()
        self.assertEqual(canvas.mode, DrawingMode.VIEW)

        # Set Draw Line mode
        canvas.set_drawing_mode(DrawingMode.DRAW_LINE)
        self.assertEqual(canvas.mode, DrawingMode.DRAW_LINE)

        # Set Draw ROI mode
        canvas.set_drawing_mode(DrawingMode.DRAW_ROI)
        self.assertEqual(canvas.mode, DrawingMode.DRAW_ROI)

        # Set Draw Trap A & Trap B mode
        canvas.set_drawing_mode(DrawingMode.DRAW_TRAP_A)
        self.assertEqual(canvas.mode, DrawingMode.DRAW_TRAP_A)
        canvas.set_drawing_mode(DrawingMode.DRAW_TRAP_B)
        self.assertEqual(canvas.mode, DrawingMode.DRAW_TRAP_B)

        # Cancel
        canvas.cancel_drawing()
        self.assertEqual(canvas.mode, DrawingMode.VIEW)

        # Set QImage frame
        q_img = QImage(640, 480, QImage.Format_RGB888)
        q_img.fill(Qt.black)
        canvas.set_frame(q_img)
        self.assertIsNotNone(canvas._current_pixmap)

    def test_dialogs(self):
        rtsp_dlg = RTSPInputDialog()
        self.assertIn("rtsp://", rtsp_dlg.get_url())

        roi_dlg = ROIConfigDialog(current_threshold=25.0, current_tolerance=15.0)
        th, tol = roi_dlg.get_values()
        self.assertEqual(th, 25.0)
        self.assertEqual(tol, 15.0)

        viewer_dlg = SnapshotViewerDialog("outputs/captures/non_existent.jpg", "Test details")
        self.assertIsNotNone(viewer_dlg)

    def test_main_window_init(self):
        window = MainWindow()
        self.assertIsNotNone(window.canvas)
        self.assertIsNotNone(window.table_violations)
        self.assertIsNotNone(window.table_plates)
        self.assertIsNotNone(window.card_total)
        self.assertIsNotNone(window.slider_conf)
        self.assertIsNotNone(window.combo_trap_lane)
        self.assertIsNotNone(window.btn_draw_trap_a)
        self.assertIsNotNone(window.btn_draw_trap_b)
        self.assertIsNotNone(window.btn_cfg_trap)
        self.assertIsNotNone(window.btn_reset_trap_defaults)
        window.close()

    def test_plate_speed_table_live_update(self):
        window = MainWindow()

        # Simulate newly recognized plate with unknown speed initially ("Đang đo...")
        plate_data = {
            "track_id": 99,
            "plate_text": "30F-999.99",
            "confidence": 0.95,
            "crop_image": None,
            "timestamp": "12:00:00",
            "speed_kmh": None,
        }
        window._on_plate_recognized(plate_data)

        self.assertEqual(window.table_plates.rowCount(), 1)
        self.assertEqual(window.table_plates.item(0, 1).text(), " 30F-999.99 ")
        self.assertEqual(window.table_plates.item(0, 2).text(), "#99")
        self.assertEqual(window.table_plates.item(0, 3).text(), "Đang đo...")

        # Now simulate Solution 1: Live speed update slot
        window._on_speed_updated(track_id=99, speed_kmh=88.4)
        self.assertEqual(window.table_plates.item(0, 3).text(), "88.4 km/h")

        # Test Dual Lane Speed Trap updates (Lane IN: index 0)
        window.combo_trap_lane.setCurrentIndex(0)
        window._on_trap_a_drawn((100, 200), (900, 200))
        self.assertEqual(window.engine.speed_trap.lane_in.line_a, ((100, 200), (900, 200)))

        # Test Dual Lane Speed Trap updates (Lane OUT: index 1)
        window.combo_trap_lane.setCurrentIndex(1)
        window._on_trap_a_drawn((600, 500), (1200, 500))
        self.assertEqual(window.engine.speed_trap.lane_out.line_a, ((600, 500), (1200, 500)))

        window.close()


if __name__ == "__main__":
    unittest.main()
