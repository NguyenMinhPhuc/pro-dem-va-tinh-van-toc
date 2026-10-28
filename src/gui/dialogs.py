"""Dialog windows for AutoGuardian GUI.

Includes:
- SnapshotViewerDialog: View violation photographic evidence in full size.
- RTSPInputDialog: Custom dialog for entering RTSP stream URLs.
- ROIConfigDialog: Set dwell time limit and stationary tolerance for parking zone.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class SnapshotViewerDialog(QDialog):
    """Dialog for viewing violation snapshot images and evidence metadata."""

    def __init__(self, image_path: str, details: Optional[str] = None, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.image_path = image_path
        self.setWindowTitle(f"Bằng chứng vi phạm - {Path(image_path).name}")
        self.resize(800, 600)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; }
            QLabel { color: #ffffff; }
            QPushButton { 
                background-color: #2d2d2d; 
                color: #ffffff; 
                padding: 6px 14px; 
                border-radius: 4px;
                border: 1px solid #3d3d3d;
            }
            QPushButton:hover { background-color: #3d3d3d; }
        """)

        layout = QVBoxLayout(self)

        # Image display
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("background-color: #121212; border: 1px solid #333333; border-radius: 4px;")

        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.img_label.setPixmap(pixmap.scaled(760, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.img_label.setText(f"Không tìm thấy file ảnh:\n{image_path}")

        layout.addWidget(self.img_label)

        # Details
        if details:
            details_label = QLabel(f"<b>Chi tiết sự kiện:</b> {details}")
            details_label.setFont(QFont("Segoe UI", 10))
            layout.addWidget(details_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_open_folder = QPushButton("Mở thư mục chứa ảnh")
        btn_open_folder.clicked.connect(self._open_folder)
        btn_layout.addWidget(btn_open_folder)

        btn_layout.addStretch()

        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _open_folder(self) -> None:
        """Opens explorer to the snapshot file."""
        if os.path.exists(self.image_path):
            os.system(f'explorer /select,"{os.path.abspath(self.image_path)}"')


class RTSPInputDialog(QDialog):
    """Dialog for inputting RTSP IP Camera stream URLs."""

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Kết nối Camera RTSP")
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; }
            QLabel { color: #e0e0e0; }
            QLineEdit { 
                background-color: #2b2b2b; 
                color: #ffffff; 
                padding: 6px; 
                border: 1px solid #444444; 
                border-radius: 4px; 
            }
            QPushButton { 
                background-color: #007acc; 
                color: #ffffff; 
                padding: 6px 12px; 
                border-radius: 4px; 
                border: none;
            }
            QPushButton:hover { background-color: #0098ff; }
        """)

        layout = QVBoxLayout(self)

        info_lbl = QLabel("Nhập URL luồng RTSP của Camera IP:")
        layout.addWidget(info_lbl)

        self.url_input = QLineEdit("rtsp://admin:admin123@192.168.1.100:554/stream1")
        layout.addWidget(self.url_input)

        hint_lbl = QLabel("<small style='color:#888888;'>Ví dụ: rtsp://username:password@ip_address:port/h264Preview_01_main</small>")
        layout.addWidget(hint_lbl)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_url(self) -> str:
        return self.url_input.text().strip()


class ROIConfigDialog(QDialog):
    """Dialog for configuring parking ROI threshold settings."""

    def __init__(self, current_threshold: float = 30.0, current_tolerance: float = 20.0, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cài đặt Ngưỡng Vùng Cấm Đỗ")
        self.setFixedWidth(380)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; }
            QLabel { color: #e0e0e0; }
            QDoubleSpinBox { 
                background-color: #2b2b2b; 
                color: #ffffff; 
                padding: 4px; 
                border: 1px solid #444444; 
                border-radius: 4px; 
            }
            QPushButton { 
                background-color: #007acc; 
                color: #ffffff; 
                padding: 6px 12px; 
                border-radius: 4px; 
                border: none;
            }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(5.0, 3600.0)
        self.spin_threshold.setValue(current_threshold)
        self.spin_threshold.setSuffix(" giây")
        form.addRow("Thời gian đỗ tối đa cho phép:", self.spin_threshold)

        self.spin_tolerance = QDoubleSpinBox()
        self.spin_tolerance.setRange(5.0, 200.0)
        self.spin_tolerance.setValue(current_tolerance)
        self.spin_tolerance.setSuffix(" pixel")
        form.addRow("Ngưỡng dịch chuyển đứng yên:", self.spin_tolerance)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_values(self) -> Tuple[float, float]:
        return self.spin_threshold.value(), self.spin_tolerance.value()

