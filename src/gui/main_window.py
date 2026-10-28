"""Main Window for AutoGuardian Desktop Application.

Provides a professional dark-themed user interface integrating live video canvas,
interactive zone drawing, AI controls, dashboard statistics, violation evidence viewer,
and reporting.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Pre-load PyTorch before PyQt5 to prevent Windows DLL resolution conflict
import torch
import cv2
from PyQt5.QtCore import QSize, Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.core.engine import AutoGuardianAIEngine
from src.gui.canvas import DrawingMode, InteractiveVideoCanvas
from src.gui.dialogs import ROIConfigDialog, RTSPInputDialog, SnapshotViewerDialog
from src.gui.worker import VideoProcessingWorker
from src.storage.database import DatabaseManager
from src.storage.evidence import EvidenceManager
from src.storage.exporter import ReportExporter
from src.storage.recorder import VideoRecorder
from src.utils.config import AppConfig


class MainWindow(QMainWindow):
    """Main application window for AutoGuardian."""

    def __init__(self, config_path: str = "configs/config.json") -> None:
        super().__init__()
        self.config = AppConfig(config_path=config_path)
        self.db = DatabaseManager(self.config.db_path)
        self.evidence = EvidenceManager(self.config.captures_dir)
        self.recorder = VideoRecorder(self.config.recordings_dir)
        self.exporter = ReportExporter(self.db, self.config.reports_dir)

        # Engine
        self.engine = AutoGuardianAIEngine(
            config=self.config,
            db_manager=self.db,
            evidence_manager=self.evidence,
            video_recorder=self.recorder,
        )

        self.worker: Optional[VideoProcessingWorker] = None
        self.current_source: Optional[Union[str, int]] = None

        # Alert configuration
        self.sound_alert_enabled: bool = True
        self.popup_alert_enabled: bool = False
        self._last_violation_alert_time: float = 0.0

        self._init_ui()
        self._apply_dark_theme()
        self._load_initial_violations()

    def _init_ui(self) -> None:
        """Initializes GUI layouts and widgets."""
        self.setWindowTitle(f"{self.config.config_data.get('system', {}).get('app_name', 'AutoGuardian')} - Hệ thống Giám sát & Bãi đỗ xe Thông minh")
        self.resize(1400, 850)
        self.setMinimumSize(1100, 700)

        # Main splitter (Left: Video & Canvas, Right: Controls & Dashboard)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left Widget: Video Player & Drawing Bar
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # Drawing & Controls Toolbar above canvas
        canvas_bar = QHBoxLayout()
        self.lbl_mode = QLabel("Chế độ: Xem trực tiếp")
        self.lbl_mode.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.lbl_mode.setStyleSheet("color: #4CAF50;")
        canvas_bar.addWidget(self.lbl_mode)

        canvas_bar.addStretch()

        self.btn_draw_line = QPushButton("✏️ Vẽ Vạch Đếm")
        self.btn_draw_line.setToolTip("Nhấp chuột và kéo trên video để định nghĩa vạch đếm xe")
        self.btn_draw_line.clicked.connect(self._on_draw_line_clicked)
        canvas_bar.addWidget(self.btn_draw_line)

        self.btn_draw_roi = QPushButton("📐 Vẽ Vùng Cấm Đỗ")
        self.btn_draw_roi.setToolTip("Nhấp các đỉnh đa giác trên video. Chuột phải hoặc nhấp đúp để hoàn tất")
        self.btn_draw_roi.clicked.connect(self._on_draw_roi_clicked)
        canvas_bar.addWidget(self.btn_draw_roi)

        self.btn_cfg_roi = QPushButton("⚙️ Cài Ngưỡng Đỗ")
        self.btn_cfg_roi.clicked.connect(self._on_configure_roi_clicked)
        canvas_bar.addWidget(self.btn_cfg_roi)

        # Speed Trap Dual Lane Controls
        self.combo_trap_lane = QComboBox()
        self.combo_trap_lane.addItems(["🚗 Làn Vào (IN)", "🚙 Làn Ra (OUT)"])
        self.combo_trap_lane.setToolTip("Chọn làn xe cần thiết lập mốc A, B hoặc khoảng cách")
        canvas_bar.addWidget(self.combo_trap_lane)

        self.btn_draw_trap_a = QPushButton("🚩 Vẽ Mốc A")
        self.btn_draw_trap_a.setToolTip("Nhấp chuột và kéo trên video để định nghĩa Mốc A cho làn đang chọn")
        self.btn_draw_trap_a.clicked.connect(self._on_draw_trap_a_clicked)
        canvas_bar.addWidget(self.btn_draw_trap_a)

        self.btn_draw_trap_b = QPushButton("🏁 Vẽ Mốc B")
        self.btn_draw_trap_b.setToolTip("Nhấp chuột và kéo trên video để định nghĩa Mốc B cho làn đang chọn")
        self.btn_draw_trap_b.clicked.connect(self._on_draw_trap_b_clicked)
        canvas_bar.addWidget(self.btn_draw_trap_b)

        self.btn_cfg_trap = QPushButton("📏 Khoảng Cách")
        self.btn_cfg_trap.setToolTip("Nhập khoảng cách thực tế giữa Mốc A và Mốc B (mét) cho làn đang chọn")
        self.btn_cfg_trap.clicked.connect(self._on_configure_speed_trap_clicked)
        canvas_bar.addWidget(self.btn_cfg_trap)

        self.btn_reset_trap_defaults = QPushButton("↺ Mặc Định")
        self.btn_reset_trap_defaults.setToolTip("Khôi phục lại tọa độ mốc mặc định chuẩn ban đầu cho cả hai làn ra/vào")
        self.btn_reset_trap_defaults.clicked.connect(self._on_reset_trap_defaults_clicked)
        canvas_bar.addWidget(self.btn_reset_trap_defaults)

        self.btn_cancel_draw = QPushButton("✖ Hủy Vẽ")
        self.btn_cancel_draw.clicked.connect(self._on_cancel_draw_clicked)
        self.btn_cancel_draw.setEnabled(False)
        canvas_bar.addWidget(self.btn_cancel_draw)

        left_layout.addLayout(canvas_bar)

        # Canvas
        self.canvas = InteractiveVideoCanvas()
        self.canvas.line_drawn.connect(self._on_line_drawn)
        self.canvas.roi_drawn.connect(self._on_roi_drawn)
        self.canvas.trap_a_drawn.connect(self._on_trap_a_drawn)
        self.canvas.trap_b_drawn.connect(self._on_trap_b_drawn)
        self.canvas.mode_changed.connect(self._on_canvas_mode_changed)
        left_layout.addWidget(self.canvas, stretch=1)

        # Playback Control Bar
        play_bar = QHBoxLayout()
        self.btn_play = QPushButton("▶ Bắt đầu")
        self.btn_play.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_play.clicked.connect(self._on_play_clicked)
        play_bar.addWidget(self.btn_play)

        self.btn_pause = QPushButton("⏸ Tạm dừng")
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        self.btn_pause.setEnabled(False)
        play_bar.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ Dừng luồng")
        self.btn_stop.setStyleSheet("background-color: #c62828; color: white; padding: 6px 14px;")
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        self.btn_stop.setEnabled(False)
        play_bar.addWidget(self.btn_stop)

        play_bar.addSpacing(20)

        self.btn_record = QPushButton("⏺ Ghi hình (REC)")
        self.btn_record.setStyleSheet("background-color: #37474f; color: white; padding: 6px 14px;")
        self.btn_record.clicked.connect(self._on_record_clicked)
        play_bar.addWidget(self.btn_record)

        self.btn_reset_counter = QPushButton("🔄 Reset Counter")
        self.btn_reset_counter.clicked.connect(self._on_reset_counter_clicked)
        play_bar.addWidget(self.btn_reset_counter)

        play_bar.addStretch()

        self.btn_export_excel = QPushButton("📊 Xuất Excel")
        self.btn_export_excel.setStyleSheet("background-color: #1b5e20; color: white; padding: 6px 12px;")
        self.btn_export_excel.clicked.connect(self._on_export_excel_clicked)
        play_bar.addWidget(self.btn_export_excel)

        self.btn_export_csv = QPushButton("📄 Xuất CSV")
        self.btn_export_csv.clicked.connect(self._on_export_csv_clicked)
        play_bar.addWidget(self.btn_export_csv)

        left_layout.addLayout(play_bar)

        splitter.addWidget(left_widget)

        # Right Widget: Control Panels, Dashboard, Violations Table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # 1. Source Controller Panel
        grp_source = QGroupBox("Nguồn Dữ Liệu Video (Input Source)")
        src_layout = QGridLayout(grp_source)

        self.btn_load_file = QPushButton("📁 Chọn Video (.mp4 / .avi)")
        self.btn_load_file.clicked.connect(self._on_load_file_clicked)
        src_layout.addWidget(self.btn_load_file, 0, 0)

        self.combo_webcam = QComboBox()
        self.combo_webcam.addItems(["Webcam 0 (Tích hợp)", "Webcam 1 (USB)", "Webcam 2 (Khác)"])
        src_layout.addWidget(self.combo_webcam, 0, 1)

        self.btn_connect_webcam = QPushButton("📹 Mở Webcam")
        self.btn_connect_webcam.clicked.connect(self._on_connect_webcam_clicked)
        src_layout.addWidget(self.btn_connect_webcam, 0, 2)

        self.btn_rtsp = QPushButton("🌐 Kết nối Camera IP (RTSP)")
        self.btn_rtsp.clicked.connect(self._on_rtsp_clicked)
        src_layout.addWidget(self.btn_rtsp, 1, 0, 1, 3)

        self.chk_loop_video = QCheckBox("🔁 Lặp lại video MP4 liên tục (Không dừng)")
        self.chk_loop_video.setChecked(True)
        self.chk_loop_video.setToolTip("Khi phát hết video, tự động lặp lại từ khung hình đầu tiên để tiếp tục giám sát")
        src_layout.addWidget(self.chk_loop_video, 2, 0, 1, 3)

        right_layout.addWidget(grp_source)

        # 2. AI Parameters & Display Overlays
        grp_ai = QGroupBox("Tham Số AI & Hiển Thị (Overlay Controls)")
        ai_layout = QVBoxLayout(grp_ai)

        # Confidence Slider
        conf_box = QHBoxLayout()
        conf_box.addWidget(QLabel("Ngưỡng tin cậy (Conf):"))
        self.slider_conf = QSlider(Qt.Horizontal)
        self.slider_conf.setRange(10, 95)
        self.slider_conf.setValue(int(self.config.default_confidence * 100))
        self.slider_conf.valueChanged.connect(self._on_conf_changed)
        conf_box.addWidget(self.slider_conf)

        self.lbl_conf_val = QLabel(f"{self.config.default_confidence:.2f}")
        self.lbl_conf_val.setFixedWidth(36)
        conf_box.addWidget(self.lbl_conf_val)
        ai_layout.addLayout(conf_box)

        # Speed Calibration Box
        speed_box = QHBoxLayout()
        speed_box.addWidget(QLabel("Tỷ lệ Pixel/Mét (Tốc độ):"))
        self.spin_ppm = QDoubleSpinBox()
        self.spin_ppm.setRange(1.0, 150.0)
        self.spin_ppm.setSingleStep(0.5)
        self.spin_ppm.setValue(self.config.pixels_per_meter)
        self.spin_ppm.setSuffix(" px/m")
        self.spin_ppm.valueChanged.connect(self._on_ppm_changed)
        speed_box.addWidget(self.spin_ppm)

        btn_preset_highway = QPushButton("🚗 Cao tốc 1080p (22 px/m)")
        btn_preset_highway.setToolTip("Gán tỷ lệ 22.0 px/m cho video Full HD 1080p cao tốc")
        btn_preset_highway.clicked.connect(lambda: self.spin_ppm.setValue(22.0))
        speed_box.addWidget(btn_preset_highway)

        btn_preset_urban = QPushButton("🏙️ Đô thị 1080p (35 px/m)")
        btn_preset_urban.setToolTip("Gán tỷ lệ 35.0 px/m cho camera góc gần / đường nội đô 1080p")
        btn_preset_urban.clicked.connect(lambda: self.spin_ppm.setValue(35.0))
        speed_box.addWidget(btn_preset_urban)

        btn_preset_720p = QPushButton("📐 720p (12 px/m)")
        btn_preset_720p.setToolTip("Gán tỷ lệ 12.0 px/m cho video HD 720p")
        btn_preset_720p.clicked.connect(lambda: self.spin_ppm.setValue(12.0))
        speed_box.addWidget(btn_preset_720p)

        ai_layout.addLayout(speed_box)

        # Overlay Checkboxes
        chk_layout = QGridLayout()
        self.chk_bbox = QCheckBox("Bounding Box")
        self.chk_bbox.setChecked(True)
        self.chk_bbox.toggled.connect(lambda v: self._toggle_overlay("show_bbox", v))
        chk_layout.addWidget(self.chk_bbox, 0, 0)

        self.chk_track_id = QCheckBox("Track ID")
        self.chk_track_id.setChecked(True)
        self.chk_track_id.toggled.connect(lambda v: self._toggle_overlay("show_track_id", v))
        chk_layout.addWidget(self.chk_track_id, 0, 1)

        self.chk_fps = QCheckBox("Hiển thị FPS")
        self.chk_fps.setChecked(True)
        self.chk_fps.toggled.connect(lambda v: self._toggle_overlay("show_fps", v))
        chk_layout.addWidget(self.chk_fps, 0, 2)

        self.chk_line = QCheckBox("Vạch Đếm Ảo")
        self.chk_line.setChecked(True)
        self.chk_line.toggled.connect(lambda v: self._toggle_overlay("show_counting_line", v))
        chk_layout.addWidget(self.chk_line, 1, 0)

        self.chk_roi = QCheckBox("Vùng Cấm Đỗ (ROI)")
        self.chk_roi.setChecked(True)
        self.chk_roi.toggled.connect(lambda v: self._toggle_overlay("show_parking_roi", v))
        chk_layout.addWidget(self.chk_roi, 1, 1)

        self.chk_trap = QCheckBox("Speed Trap (2 Mốc)")
        self.chk_trap.setChecked(True)
        self.chk_trap.toggled.connect(lambda v: self._toggle_overlay("show_speed_trap", v))
        chk_layout.addWidget(self.chk_trap, 1, 2)

        ai_layout.addLayout(chk_layout)
        right_layout.addWidget(grp_ai)

        # 3. Real-time Dashboard
        grp_dash = QGroupBox("Chỉ Số Giám Sát Thời Gian Thực (Dashboard)")
        dash_layout = QGridLayout(grp_dash)

        self.card_total = self._create_stat_card("Tổng Xe Đếm", "0", "#00bcd4")
        dash_layout.addWidget(self.card_total, 0, 0)

        self.card_in = self._create_stat_card("Chiều Vào (IN)", "0", "#4caf50")
        dash_layout.addWidget(self.card_in, 0, 1)

        self.card_out = self._create_stat_card("Chiều Ra (OUT)", "0", "#ff9800")
        dash_layout.addWidget(self.card_out, 0, 2)

        self.card_violation = self._create_stat_card("Vi Phạm Đỗ Xe", "0", "#f44336")
        dash_layout.addWidget(self.card_violation, 1, 0)

        self.card_fps = self._create_stat_card("Tốc Độ FPS", "0.0", "#9c27b0")
        dash_layout.addWidget(self.card_fps, 1, 1)

        self.card_roi_active = self._create_stat_card("Xe Trong Vùng Cấm", "0", "#e91e63")
        dash_layout.addWidget(self.card_roi_active, 1, 2)

        # Alert banner
        self.lbl_alert_banner = QLabel("Trạng thái: Bình thường")
        self.lbl_alert_banner.setAlignment(Qt.AlignCenter)
        self.lbl_alert_banner.setStyleSheet(
            "background-color: #1b5e20; color: white; font-weight: bold; padding: 6px; border-radius: 4px;"
        )
        dash_layout.addWidget(self.lbl_alert_banner, 2, 0, 1, 3)

        # Sound & Popup alert toggles
        alert_ctrl_box = QHBoxLayout()
        self.chk_sound = QCheckBox("Chuông âm thanh")
        self.chk_sound.setChecked(True)
        self.chk_sound.toggled.connect(lambda v: setattr(self, "sound_alert_enabled", v))
        alert_ctrl_box.addWidget(self.chk_sound)

        self.chk_popup = QCheckBox("Popup cảnh báo")
        self.chk_popup.setChecked(False)
        self.chk_popup.toggled.connect(lambda v: setattr(self, "popup_alert_enabled", v))
        alert_ctrl_box.addWidget(self.chk_popup)

        self.btn_test_sound = QPushButton("🔔 Thử Âm Thanh")
        self.btn_test_sound.clicked.connect(self._on_test_sound_clicked)
        alert_ctrl_box.addWidget(self.btn_test_sound)

        dash_layout.addLayout(alert_ctrl_box, 3, 0, 1, 3)

        right_layout.addWidget(grp_dash)

        # 4. Tabbed Panel: Real-time Plate Feed & Violation Evidence
        self.tabs_records = QTabWidget()
        self.tabs_records.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2d2d2d; background-color: #161616; border-radius: 4px; }
            QTabBar::tab { background-color: #242424; color: #aaaaaa; padding: 6px 14px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background-color: #007acc; color: #ffffff; font-weight: bold; }
            QTabBar::tab:hover { background-color: #333333; }
        """)

        # Tab 1: Real-time License Plate Feed
        tab_plates = QWidget()
        layout_plates = QVBoxLayout(tab_plates)
        layout_plates.setContentsMargins(4, 4, 4, 4)

        self.table_plates = QTableWidget()
        self.table_plates.setColumnCount(5)
        self.table_plates.setHorizontalHeaderLabels(["Ảnh Biển Số", "Biển Số Xe", "Mã Xe", "Vận Tốc", "Thời Gian"])
        self.table_plates.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_plates.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_plates.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_plates.setIconSize(QSize(100, 36))
        layout_plates.addWidget(self.table_plates)
        self.tabs_records.addTab(tab_plates, "📋 Biển Số Real-time")

        # Tab 2: Violation Evidence Viewer
        tab_violations = QWidget()
        layout_violations = QVBoxLayout(tab_violations)
        layout_violations.setContentsMargins(4, 4, 4, 4)

        self.table_violations = QTableWidget()
        self.table_violations.setColumnCount(5)
        self.table_violations.setHorizontalHeaderLabels(["ID", "Thời Gian", "Mã Xe", "Thời Gian Đỗ", "Ảnh Bằng Chứng"])
        self.table_violations.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_violations.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_violations.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_violations.itemDoubleClicked.connect(self._on_table_item_double_clicked)
        layout_violations.addWidget(self.table_violations)
        self.tabs_records.addTab(tab_violations, "🚨 Vi Phạm Đỗ Xe")

        right_layout.addWidget(self.tabs_records, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setSizes([850, 550])

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng.")

    def _create_stat_card(self, title: str, initial_val: str, color_hex: str) -> QFrame:
        """Creates a modern styled stat card frame."""
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: #1e1e1e; border: 1px solid #333333; border-left: 4px solid {color_hex}; border-radius: 4px; padding: 6px;"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 8))
        lbl_title.setStyleSheet("color: #aaaaaa; border: none;")
        layout.addWidget(lbl_title)

        lbl_val = QLabel(initial_val)
        lbl_val.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_val.setStyleSheet(f"color: {color_hex}; border: none;")
        layout.addWidget(lbl_val)

        # Save reference for dynamic updates
        setattr(frame, "val_label", lbl_val)
        return frame

    def _apply_dark_theme(self) -> None:
        """Applies sleek dark QSS theme to the entire application."""
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; color: #ffffff; }
            QWidget { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #2d2d2d; 
                border-radius: 6px; 
                margin-top: 10px; 
                padding-top: 12px;
                color: #ffffff;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPushButton { 
                background-color: #2a2a2a; 
                color: #ffffff; 
                border: 1px solid #3d3d3d; 
                border-radius: 4px; 
                padding: 5px 12px;
            }
            QPushButton:hover { background-color: #383838; }
            QPushButton:pressed { background-color: #1f1f1f; }
            QPushButton:disabled { background-color: #1a1a1a; color: #666666; border-color: #222222; }
            QComboBox { background-color: #222222; border: 1px solid #3d3d3d; border-radius: 4px; padding: 4px; color: #ffffff; }
            QTableWidget { 
                background-color: #181818; 
                alternate-background-color: #202020; 
                gridline-color: #2d2d2d; 
                border: 1px solid #2d2d2d;
                border-radius: 4px;
            }
            QHeaderView::section { background-color: #242424; color: #ffffff; font-weight: bold; padding: 4px; border: 1px solid #333333; }
            QSlider::groove:horizontal { height: 4px; background: #333333; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #00bcd4; border-radius: 2px; }
            QSlider::handle:horizontal { background: #ffffff; width: 14px; margin-top: -5px; margin-bottom: -5px; border-radius: 7px; }
            QStatusBar { background-color: #181818; color: #888888; }
        """)

    # -------------------------------------------------------------
    # Source & Playback Handlers
    # -------------------------------------------------------------
    def _on_load_file_clicked(self) -> None:
        """Opens file dialog to choose a video file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file video",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)",
        )
        if file_path:
            self.current_source = file_path
            self.status_bar.showMessage(f"Đã chọn file: {Path(file_path).name}")
            self._start_stream()

    def _on_connect_webcam_clicked(self) -> None:
        """Connects to selected webcam index."""
        idx = self.combo_webcam.currentIndex()
        self.current_source = idx
        self.status_bar.showMessage(f"Đã chọn Webcam #{idx}")
        self._start_stream()

    def _on_rtsp_clicked(self) -> None:
        """Opens dialog to enter RTSP stream URL."""
        dlg = RTSPInputDialog(self)
        if dlg.exec_() == RTSPInputDialog.Accepted:
            url = dlg.get_url()
            if url:
                self.current_source = url
                self.status_bar.showMessage(f"Đã kết nối RTSP: {url}")
                self._start_stream()

    def _start_stream(self) -> None:
        """Starts worker thread for currently selected source."""
        if self.current_source is None:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn nguồn video (File, Webcam hoặc RTSP) trước!")
            return

        # Stop existing worker if running
        if self.worker is not None:
            self.worker.stop()
            self.worker = None

        self.worker = VideoProcessingWorker(
            source=self.current_source,
            engine=self.engine,
            loop_video=self.chk_loop_video.isChecked(),
            parent=self,
        )

        # Connect worker signals
        self.worker.frame_ready.connect(self._on_frame_ready)
        self.worker.fps_updated.connect(self._on_fps_updated)
        self.worker.stats_updated.connect(self._on_stats_updated)
        self.worker.violation_detected.connect(self._on_violation_detected)
        self.worker.plate_recognized.connect(self._on_plate_recognized)
        self.worker.speed_updated.connect(self._on_speed_updated)
        self.worker.status_message.connect(lambda msg: self.status_bar.showMessage(msg))
        self.worker.stream_ended.connect(self._on_stream_ended)
        self.worker.recording_status_changed.connect(self._on_recording_status_changed)

        self.worker.start()

        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

    def _on_play_clicked(self) -> None:
        if self.worker is not None and self.worker._is_paused:
            self.worker.resume()
            self.btn_play.setEnabled(False)
            self.btn_pause.setEnabled(True)
        elif self.current_source is not None:
            self._start_stream()

    def _on_pause_clicked(self) -> None:
        if self.worker is not None:
            self.worker.pause()
            self.btn_play.setEnabled(True)
            self.btn_pause.setEnabled(False)

    def _on_stop_clicked(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.status_bar.showMessage("Đã dừng luồng.")

    def _on_stream_ended(self) -> None:
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

    # -------------------------------------------------------------
    # Worker Signal Slots
    # -------------------------------------------------------------
    @pyqtSlot(QImage, object)
    def _on_frame_ready(self, q_img: QImage, result: Any) -> None:
        """Receives processed QImage and updates canvas."""
        self.canvas.set_frame(q_img)
        self.card_roi_active.val_label.setText(str(result.active_in_roi))

    @pyqtSlot(float)
    def _on_fps_updated(self, fps: float) -> None:
        self.card_fps.val_label.setText(f"{fps:.1f}")

    @pyqtSlot(int, int, int, int)
    def _on_stats_updated(self, total: int, inc: int, outc: int, viols: int) -> None:
        self.card_total.val_label.setText(str(total))
        self.card_in.val_label.setText(str(inc))
        self.card_out.val_label.setText(str(outc))
        self.card_violation.val_label.setText(str(viols))

    @pyqtSlot(dict)
    def _on_plate_recognized(self, p_data: Dict[str, Any]) -> None:
        """Adds a newly recognized license plate to the live plate feed table."""
        row = 0
        self.table_plates.insertRow(row)

        # 0. Thumbnail Crop
        crop_img = p_data.get("crop_image")
        if crop_img is not None and crop_img.size > 0:
            h, w, ch = crop_img.shape
            rgb_thumb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
            q_thumb = QImage(rgb_thumb.data, w, h, ch * w, QImage.Format_RGB888)
            pix = QPixmap.fromImage(q_thumb).scaled(90, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item_thumb = QTableWidgetItem()
            item_thumb.setIcon(QIcon(pix))
            self.table_plates.setItem(row, 0, item_thumb)
        else:
            self.table_plates.setItem(row, 0, QTableWidgetItem("-"))

        # 1. Plate Text
        plate_str = p_data.get("plate_text", "---")
        item_plate = QTableWidgetItem(f" {plate_str} ")
        item_plate.setFont(QFont("Segoe UI", 10, QFont.Bold))
        item_plate.setForeground(QColor("#00ff88"))
        item_plate.setTextAlignment(Qt.AlignCenter)
        self.table_plates.setItem(row, 1, item_plate)

        # 2. Track ID
        tid = p_data.get("track_id", "?")
        item_id = QTableWidgetItem(f"#{tid}")
        item_id.setTextAlignment(Qt.AlignCenter)
        self.table_plates.setItem(row, 2, item_id)

        # 3. Speed (km/h)
        speed = p_data.get("speed_kmh")
        if (speed is None or speed <= 0) and isinstance(tid, int):
            speed = self.engine.speed_trap.get_trap_speed(tid) or self.engine.speed_estimator.get_speed(tid)
        spd_str = f"{speed:.1f} km/h" if speed is not None and speed > 0 else "Đang đo..."
        item_speed = QTableWidgetItem(spd_str)
        item_speed.setTextAlignment(Qt.AlignCenter)
        item_speed.setForeground(QColor("#00ff88") if speed and speed > 0 else QColor("#00bcd4"))
        self.table_plates.setItem(row, 3, item_speed)

        # 4. Timestamp
        ts = p_data.get("timestamp", "")
        item_ts = QTableWidgetItem(ts)
        item_ts.setTextAlignment(Qt.AlignCenter)
        self.table_plates.setItem(row, 4, item_ts)

        # Cap rows to 100 on edge devices
        if self.table_plates.rowCount() > 100:
            self.table_plates.removeRow(self.table_plates.rowCount() - 1)

    @pyqtSlot(int, float)
    def _on_speed_updated(self, track_id: int, speed_kmh: float) -> None:
        """Dynamically updates the speed cell for a tracked vehicle in the plate feed."""
        if speed_kmh <= 0:
            return
        spd_str = f"{speed_kmh:.1f} km/h"
        target_id_str = f"#{track_id}"
        for r in range(self.table_plates.rowCount()):
            id_item = self.table_plates.item(r, 2)
            if id_item and id_item.text() == target_id_str:
                spd_item = self.table_plates.item(r, 3)
                if spd_item and spd_item.text() != spd_str:
                    spd_item.setText(spd_str)
                    spd_item.setForeground(QColor("#00ff88"))

    @pyqtSlot(dict)
    def _on_violation_detected(self, vi: Dict[str, Any]) -> None:
        """Handles incoming violation alert."""
        # Visual alert
        self.lbl_alert_banner.setText(f"🚨 CẢNH BÁO: XE #{vi['track_id']} ĐỖ XE TRÁI PHÉP!")
        self.lbl_alert_banner.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: bold; padding: 6px; border-radius: 4px;"
        )

        # Sound alert
        if self.sound_alert_enabled:
            QApplication.beep()

        # Add to table
        self._add_violation_row(vi)

        # Reset banner after 4 seconds
        QTimer.singleShot(4000, self._reset_alert_banner)

        # Popup alert if enabled
        if self.popup_alert_enabled:
            QMessageBox.warning(
                self,
                "Cảnh Báo Đỗ Xe Trái Phép",
                f"Phát hiện phương tiện #{vi['track_id']} đỗ quá thời gian quy định tại {vi.get('zone_name', 'vùng cấm')}!\nĐã chụp ảnh bằng chứng.",
            )

    def _reset_alert_banner(self) -> None:
        self.lbl_alert_banner.setText("Trạng thái: Giám sát bình thường")
        self.lbl_alert_banner.setStyleSheet(
            "background-color: #1b5e20; color: white; font-weight: bold; padding: 6px; border-radius: 4px;"
        )

    # -------------------------------------------------------------
    # Interactive Drawing & Zone Slots
    # -------------------------------------------------------------
    def _on_draw_line_clicked(self) -> None:
        self.canvas.set_drawing_mode(DrawingMode.DRAW_LINE)
        self.btn_cancel_draw.setEnabled(True)

    def _on_draw_roi_clicked(self) -> None:
        self.canvas.set_drawing_mode(DrawingMode.DRAW_ROI)
        self.btn_cancel_draw.setEnabled(True)

    def _current_trap_lane_key(self) -> str:
        """Returns 'in' or 'out' based on selected lane in combo_trap_lane."""
        return "in" if self.combo_trap_lane.currentIndex() == 0 else "out"

    def _current_trap_lane_name(self) -> str:
        return "Làn Vào (IN)" if self._current_trap_lane_key() == "in" else "Làn Ra (OUT)"

    def _on_draw_trap_a_clicked(self) -> None:
        lane_name = self._current_trap_lane_name()
        self.canvas.set_drawing_mode(DrawingMode.DRAW_TRAP_A)
        self.btn_cancel_draw.setEnabled(True)
        self.status_bar.showMessage(f"Nhấp & Kéo chuột trên video để vẽ Mốc A cho {lane_name}")

    def _on_draw_trap_b_clicked(self) -> None:
        lane_name = self._current_trap_lane_name()
        self.canvas.set_drawing_mode(DrawingMode.DRAW_TRAP_B)
        self.btn_cancel_draw.setEnabled(True)
        self.status_bar.showMessage(f"Nhấp & Kéo chuột trên video để vẽ Mốc B cho {lane_name}")

    def _on_cancel_draw_clicked(self) -> None:
        self.canvas.cancel_drawing()
        self.btn_cancel_draw.setEnabled(False)

    def _on_canvas_mode_changed(self, mode_str: str) -> None:
        self.lbl_mode.setText(f"Chế độ: {mode_str}")
        if "Xem" in mode_str:
            self.lbl_mode.setStyleSheet("color: #4CAF50;")
            self.btn_cancel_draw.setEnabled(False)
        else:
            self.lbl_mode.setStyleSheet("color: #FFC107;")

    def _on_line_drawn(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> None:
        """Updates counting line in worker and engine."""
        if self.worker:
            self.worker.update_counting_line(p1, p2)
        else:
            self.engine.update_counting_line(p1, p2)
        self.status_bar.showMessage(f"Đã cập nhật Vạch đếm mới: {p1} -> {p2}")

    def _on_roi_drawn(self, points: List[Tuple[int, int]]) -> None:
        """Updates parking ROI polygon in worker and engine."""
        if self.worker:
            self.worker.update_parking_roi(points)
        else:
            self.engine.update_parking_roi(points)
        self.status_bar.showMessage(f"Đã cập nhật Vùng cấm đỗ mới gồm {len(points)} đỉnh.")

    def _on_trap_a_drawn(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> None:
        """Updates speed trap Line A for selected lane in worker and engine."""
        lane_key = self._current_trap_lane_key()
        lane_name = self._current_trap_lane_name()
        if self.worker:
            self.worker.update_speed_trap_line_a(p1, p2, lane_key=lane_key)
        else:
            self.engine.update_speed_trap_line_a(p1, p2, lane_key=lane_key)
        self.status_bar.showMessage(f"Đã cập nhật Mốc A cho {lane_name}: {p1} -> {p2}")

    def _on_trap_b_drawn(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> None:
        """Updates speed trap Line B for selected lane in worker and engine."""
        lane_key = self._current_trap_lane_key()
        lane_name = self._current_trap_lane_name()
        if self.worker:
            self.worker.update_speed_trap_line_b(p1, p2, lane_key=lane_key)
        else:
            self.engine.update_speed_trap_line_b(p1, p2, lane_key=lane_key)
        self.status_bar.showMessage(f"Đã cập nhật Mốc B cho {lane_name}: {p1} -> {p2}")

    def _on_configure_speed_trap_clicked(self) -> None:
        """Prompts dialog to configure physical distance for selected lane."""
        lane_key = self._current_trap_lane_key()
        lane_name = self._current_trap_lane_name()
        current_dist = self.engine.speed_trap.get_lane(lane_key).distance_meters
        dist, ok = QInputDialog.getDouble(
            self,
            f"Cấu Hình Khoảng Cách Mốc - {lane_name}",
            f"Nhập khoảng cách thực tế giữa Mốc A và Mốc B cho {lane_name} (mét):",
            value=current_dist,
            min=1.0,
            max=1000.0,
            decimals=1,
        )
        if ok:
            if self.worker:
                self.worker.update_speed_trap_distance(dist, enabled=True, lane_key=lane_key)
            else:
                self.engine.update_speed_trap_distance(dist, enabled=True, lane_key=lane_key)
            self.status_bar.showMessage(f"Đã cập nhật khoảng cách {lane_name}: {dist:.1f} mét")

    def _on_reset_trap_defaults_clicked(self) -> None:
        """Resets both lane speed traps to default benchmark lines."""
        reply = QMessageBox.question(
            self,
            "Khôi phục Mốc Mặc Định",
            "Bạn có muốn khôi phục lại vị trí Mốc A và Mốc B mặc định chuẩn cho cả Làn Vào và Làn Ra?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            if self.worker:
                self.worker.reset_speed_trap_to_defaults()
            else:
                self.engine.reset_speed_trap_to_defaults()
            self.status_bar.showMessage("Đã khôi phục mốc đo vận tốc Làn Vào & Làn Ra về giá trị mặc định chuẩn.")

    def _on_configure_roi_clicked(self) -> None:
        """Opens dialog to configure parking time limit."""
        current_th = self.engine.parking_analyzer.threshold_seconds
        current_tol = self.engine.parking_analyzer.displacement_tolerance
        dlg = ROIConfigDialog(current_th, current_tol, self)
        if dlg.exec_() == ROIConfigDialog.Accepted:
            new_th, new_tol = dlg.get_values()
            self.engine.parking_analyzer.threshold_seconds = new_th
            self.engine.parking_analyzer.displacement_tolerance = new_tol
            self.status_bar.showMessage(f"Đã cập nhật ngưỡng đỗ: {new_th:.0f}s, độ dịch chuyển: {new_tol:.0f}px")

    # -------------------------------------------------------------
    # AI & Overlay Options
    # -------------------------------------------------------------
    def _on_conf_changed(self, val: int) -> None:
        conf = float(val) / 100.0
        self.lbl_conf_val.setText(f"{conf:.2f}")
        if self.worker:
            self.worker.set_confidence(conf)
        else:
            self.engine.set_confidence(conf)

    def _on_ppm_changed(self, val: float) -> None:
        """Updates speed estimation scale ratio."""
        if self.worker:
            self.worker.set_pixels_per_meter(val)
        else:
            self.engine.set_pixels_per_meter(val)
        self.status_bar.showMessage(f"Đã cập nhật hệ số tốc độ: {val:.1f} pixels/mét")

    def _toggle_overlay(self, option_name: str, enabled: bool) -> None:
        if self.worker:
            self.worker.set_overlay_option(option_name, enabled)
        else:
            self.engine.set_overlay_option(option_name, enabled)

    # -------------------------------------------------------------
    # Recording & Reset Handlers
    # -------------------------------------------------------------
    def _on_record_clicked(self) -> None:
        if self.worker is not None:
            is_rec = self.worker.toggle_recording()
            if is_rec:
                self.btn_record.setText("⏹ Dừng Ghi")
                self.btn_record.setStyleSheet("background-color: #d32f2f; color: white; padding: 6px 14px;")
            else:
                self.btn_record.setText("⏺ Ghi hình (REC)")
                self.btn_record.setStyleSheet("background-color: #37474f; color: white; padding: 6px 14px;")
        else:
            QMessageBox.information(self, "Thông báo", "Vui lòng bắt đầu phát video trước khi ghi hình!")

    def _on_recording_status_changed(self, is_rec: bool, msg: str) -> None:
        self.status_bar.showMessage(msg)

    def _on_reset_counter_clicked(self) -> None:
        """Prompts confirmation dialog and resets counter statistics."""
        reply = QMessageBox.question(
            self,
            "Xác nhận Reset Counter",
            "Bạn có chắc chắn muốn đặt lại toàn bộ số đếm xe và danh sách vi phạm về 0?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self.worker:
                self.worker.reset_counters()
            else:
                self.engine.reset_counters()

            self.card_total.val_label.setText("0")
            self.card_in.val_label.setText("0")
            self.card_out.val_label.setText("0")
            self.card_violation.val_label.setText("0")
            self.card_roi_active.val_label.setText("0")
            self.table_violations.setRowCount(0)
            self.table_plates.setRowCount(0)
            self.status_bar.showMessage("Đã đặt lại bộ đếm thành công.")

    def _on_test_sound_clicked(self) -> None:
        QApplication.beep()
        self.status_bar.showMessage("Đã phát âm thanh thử nghiệm.")

    # -------------------------------------------------------------
    # Export Handlers
    # -------------------------------------------------------------
    def _on_export_excel_clicked(self) -> None:
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu báo cáo Excel",
            f"outputs/reports/BAO_CAO_AUTOGUARDIAN.xlsx",
            "Excel Files (*.xlsx)",
        )
        if save_path:
            exported = self.exporter.export_to_excel(save_path)
            if exported:
                QMessageBox.information(self, "Xuất thành công", f"Đã xuất báo cáo Excel thành công tại:\n{exported}")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xuất file Excel. Vui lòng kiểm tra quyền ghi tệp!")

    def _on_export_csv_clicked(self) -> None:
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu báo cáo CSV",
            f"outputs/reports/BAO_CAO_LUU_LUONG.csv",
            "CSV Files (*.csv)",
        )
        if save_path:
            exported = self.exporter.export_to_csv(save_path)
            if exported:
                QMessageBox.information(self, "Xuất thành công", f"Đã xuất báo cáo CSV thành công tại:\n{exported}")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xuất file CSV!")

    # -------------------------------------------------------------
    # Violations Table Management
    # -------------------------------------------------------------
    def _load_initial_violations(self) -> None:
        """Loads historical violations from SQLite database into table."""
        records = self.db.get_all_violations(limit=50)
        for rec in reversed(records):
            self._add_violation_row({
                "id": rec["id"],
                "timestamp": rec["timestamp"],
                "track_id": rec["track_id"],
                "dwell_time": rec["duration_seconds"],
                "snapshot_path": rec["snapshot_path"],
                "details": rec["details"],
            })

    def _add_violation_row(self, vi: Dict[str, Any]) -> None:
        """Appends a new row to the violations table."""
        row = 0
        self.table_violations.insertRow(row)

        v_id = str(vi.get("id", self.table_violations.rowCount()))
        ts = vi.get("timestamp", Path(vi.get("snapshot_path", "")).stem.split("_")[-1] if vi.get("snapshot_path") else "")
        track_id = f"#{vi['track_id']}"
        dwell = f"{vi.get('dwell_time', 0.0):.1f}s"
        snap = Path(vi.get("snapshot_path", "")).name if vi.get("snapshot_path") else "Chưa có"

        self.table_violations.setItem(row, 0, QTableWidgetItem(v_id))
        self.table_violations.setItem(row, 1, QTableWidgetItem(ts))
        self.table_violations.setItem(row, 2, QTableWidgetItem(track_id))
        self.table_violations.setItem(row, 3, QTableWidgetItem(dwell))

        snap_item = QTableWidgetItem(snap)
        snap_item.setData(Qt.UserRole, vi.get("snapshot_path", ""))
        snap_item.setData(Qt.UserRole + 1, vi.get("details", ""))
        self.table_violations.setItem(row, 4, snap_item)

    def _on_table_item_double_clicked(self, item: QTableWidgetItem) -> None:
        """Opens snapshot viewer when double clicking table row."""
        row = item.row()
        snap_item = self.table_violations.item(row, 4)
        if snap_item:
            snap_path = snap_item.data(Qt.UserRole)
            details = snap_item.data(Qt.UserRole + 1)
            if snap_path and os.path.exists(snap_path):
                dlg = SnapshotViewerDialog(snap_path, details, self)
                dlg.exec_()
            else:
                QMessageBox.warning(self, "Thông báo", f"Không tìm thấy file ảnh chụp tại:\n{snap_path}")

    def closeEvent(self, event: Any) -> None:
        """Ensures worker and camera release when window is closed."""
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        event.accept()
