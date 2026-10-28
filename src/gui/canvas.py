"""Interactive Canvas Drawer for AutoGuardian.

Displays the video stream and allows users to click and drag to draw or adjust
virtual counting lines and polygon parking ROI zones directly on the video.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple
from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QLabel


class DrawingMode(Enum):
    """Drawing mode states for interactive canvas."""

    VIEW = 0
    DRAW_LINE = 1
    DRAW_ROI = 2
    DRAW_TRAP_A = 3
    DRAW_TRAP_B = 4


class InteractiveVideoCanvas(QLabel):
    """Custom QLabel canvas for displaying video and drawing zones interactively."""

    line_drawn = pyqtSignal(tuple, tuple)    # (p1, p2) in image coordinates
    roi_drawn = pyqtSignal(list)            # list of (x, y) in image coordinates
    trap_a_drawn = pyqtSignal(tuple, tuple)  # Line A (p1, p2)
    trap_b_drawn = pyqtSignal(tuple, tuple)  # Line B (p1, p2)
    mode_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(640, 360)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #121212; border: 1px solid #2d2d2d; border-radius: 6px;")
        self.setMouseTracking(True)

        self._current_pixmap: Optional[QPixmap] = None
        self._raw_frame_width: int = 1280
        self._raw_frame_height: int = 720

        # Drawing state
        self.mode: DrawingMode = DrawingMode.VIEW
        self._line_start: Optional[QPoint] = None
        self._line_end: Optional[QPoint] = None
        self._roi_points: List[QPoint] = []
        self._mouse_current_pos: Optional[QPoint] = None

    def set_frame(self, q_img: QImage) -> None:
        """Updates the canvas with a new QImage frame."""
        self._raw_frame_width = q_img.width()
        self._raw_frame_height = q_img.height()
        self._current_pixmap = QPixmap.fromImage(q_img)
        self.update()

    def set_drawing_mode(self, mode: DrawingMode) -> None:
        """Sets the interactive drawing mode."""
        self.mode = mode
        self._line_start = None
        self._line_end = None
        self._roi_points.clear()
        self._mouse_current_pos = None

        mode_name = "Chế độ xem"
        if mode == DrawingMode.DRAW_LINE:
            mode_name = "Đang vẽ Vạch đếm (Nhấp & Kéo chuột)"
            self.setCursor(Qt.CrossCursor)
        elif mode == DrawingMode.DRAW_ROI:
            mode_name = "Đang vẽ Vùng cấm đỗ (Nhấp các điểm, Chuột phải để hoàn tất)"
            self.setCursor(Qt.CrossCursor)
        elif mode == DrawingMode.DRAW_TRAP_A:
            mode_name = "Đang vẽ Mốc A - Bắt đầu (Nhấp & Kéo chuột)"
            self.setCursor(Qt.CrossCursor)
        elif mode == DrawingMode.DRAW_TRAP_B:
            mode_name = "Đang vẽ Mốc B - Kết thúc (Nhấp & Kéo chuột)"
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        self.mode_changed.emit(mode_name)
        self.update()

    def cancel_drawing(self) -> None:
        """Cancels current drawing operation and returns to VIEW mode."""
        self.set_drawing_mode(DrawingMode.VIEW)

    def _get_scaled_rect(self) -> Tuple[int, int, int, int]:
        """Calculates destination rectangle of pixmap keeping aspect ratio."""
        if self._current_pixmap is None:
            return 0, 0, self.width(), self.height()

        pix_w = self._current_pixmap.width()
        pix_h = self._current_pixmap.height()
        lbl_w = self.width()
        lbl_h = self.height()

        ratio = min(lbl_w / max(1, pix_w), lbl_h / max(1, pix_h))
        dest_w = int(pix_w * ratio)
        dest_h = int(pix_h * ratio)
        dest_x = int((lbl_w - dest_w) / 2)
        dest_y = int((lbl_h - dest_h) / 2)

        return dest_x, dest_y, dest_w, dest_h

    def _widget_to_image_coords(self, pt: QPoint) -> Optional[Tuple[int, int]]:
        """Maps widget pixel coordinates to original image coordinates."""
        dest_x, dest_y, dest_w, dest_h = self._get_scaled_rect()
        if dest_w <= 0 or dest_h <= 0:
            return None

        # Check bounds
        if not (dest_x <= pt.x() <= dest_x + dest_w and dest_y <= pt.y() <= dest_y + dest_h):
            return None

        img_x = int((pt.x() - dest_x) * (self._raw_frame_width / dest_w))
        img_y = int((pt.y() - dest_y) * (self._raw_frame_height / dest_h))
        img_x = max(0, min(self._raw_frame_width, img_x))
        img_y = max(0, min(self._raw_frame_height, img_y))
        return img_x, img_y

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handles mouse press for drawing lines and polygons."""
        if event.button() == Qt.LeftButton:
            if self.mode in (DrawingMode.DRAW_LINE, DrawingMode.DRAW_TRAP_A, DrawingMode.DRAW_TRAP_B):
                self._line_start = event.pos()
                self._line_end = event.pos()
                self.update()
            elif self.mode == DrawingMode.DRAW_ROI:
                self._roi_points.append(event.pos())
                self.update()
        elif event.button() == Qt.RightButton:
            # Right-click finishes polygon drawing
            if self.mode == DrawingMode.DRAW_ROI:
                self._finish_roi_drawing()
            elif self.mode in (DrawingMode.DRAW_LINE, DrawingMode.DRAW_TRAP_A, DrawingMode.DRAW_TRAP_B):
                self.cancel_drawing()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handles mouse movement for live preview of shapes."""
        self._mouse_current_pos = event.pos()
        if self.mode in (DrawingMode.DRAW_LINE, DrawingMode.DRAW_TRAP_A, DrawingMode.DRAW_TRAP_B) and self._line_start is not None:
            self._line_end = event.pos()
            self.update()
        elif self.mode == DrawingMode.DRAW_ROI:
            self.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handles mouse release to finalize line drawing."""
        if event.button() == Qt.LeftButton and self.mode in (DrawingMode.DRAW_LINE, DrawingMode.DRAW_TRAP_A, DrawingMode.DRAW_TRAP_B):
            if self._line_start is not None and self._line_end is not None:
                p1_img = self._widget_to_image_coords(self._line_start)
                p2_img = self._widget_to_image_coords(self._line_end)

                if p1_img and p2_img and (p1_img != p2_img):
                    if self.mode == DrawingMode.DRAW_LINE:
                        self.line_drawn.emit(p1_img, p2_img)
                    elif self.mode == DrawingMode.DRAW_TRAP_A:
                        self.trap_a_drawn.emit(p1_img, p2_img)
                    elif self.mode == DrawingMode.DRAW_TRAP_B:
                        self.trap_b_drawn.emit(p1_img, p2_img)

            self.set_drawing_mode(DrawingMode.VIEW)

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-click also finishes polygon drawing."""
        if self.mode == DrawingMode.DRAW_ROI:
            self._finish_roi_drawing()
        super().mouseDoubleClickEvent(event)

    def _finish_roi_drawing(self) -> None:
        """Converts accumulated widget points to image points and emits roi_drawn signal."""
        if len(self._roi_points) >= 3:
            img_points = []
            for pt in self._roi_points:
                mapped = self._widget_to_image_coords(pt)
                if mapped:
                    img_points.append(mapped)

            if len(img_points) >= 3:
                self.roi_drawn.emit(img_points)

        self.set_drawing_mode(DrawingMode.VIEW)

    def paintEvent(self, event: Any) -> None:
        """Custom paint event to draw the video frame and interactive drawing overlays."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Draw video pixmap
        if self._current_pixmap is not None:
            dest_x, dest_y, dest_w, dest_h = self._get_scaled_rect()
            scaled = self._current_pixmap.scaled(
                dest_w, dest_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            painter.drawPixmap(dest_x, dest_y, scaled)
        else:
            # Draw placeholder when no video is loaded
            painter.setPen(QColor("#777777"))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "Chưa nạp nguồn Video / Camera\n(Bấm 'Nạp Video' hoặc 'Kết nối Camera' để bắt đầu)")

        # 2. Draw live line rubberband
        if self.mode in (DrawingMode.DRAW_LINE, DrawingMode.DRAW_TRAP_A, DrawingMode.DRAW_TRAP_B) and self._line_start and self._line_end:
            if self.mode == DrawingMode.DRAW_TRAP_A:
                line_color = QColor(0, 200, 255)  # Cyan for Trap A
            elif self.mode == DrawingMode.DRAW_TRAP_B:
                line_color = QColor(0, 255, 128)  # Neon Green for Trap B
            else:
                line_color = QColor(255, 230, 0)  # Yellow for Counting Line

            pen = QPen(line_color, 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(self._line_start, self._line_end)
            painter.setBrush(line_color)
            painter.drawEllipse(self._line_start, 4, 4)
            painter.drawEllipse(self._line_end, 4, 4)

        # 3. Draw live polygon ROI
        if self.mode == DrawingMode.DRAW_ROI and len(self._roi_points) > 0:
            pen = QPen(QColor(0, 255, 128), 2, Qt.SolidLine)
            painter.setPen(pen)

            # Draw vertices
            painter.setBrush(QColor(0, 255, 128))
            for pt in self._roi_points:
                painter.drawEllipse(pt, 4, 4)

            # Draw lines between existing vertices
            for i in range(len(self._roi_points) - 1):
                painter.drawLine(self._roi_points[i], self._roi_points[i + 1])

            # Draw rubberband to current mouse cursor
            if self._mouse_current_pos is not None:
                pen_guide = QPen(QColor(0, 255, 128), 1, Qt.DashLine)
                painter.setPen(pen_guide)
                painter.drawLine(self._roi_points[-1], self._mouse_current_pos)
                if len(self._roi_points) >= 2:
                    painter.drawLine(self._mouse_current_pos, self._roi_points[0])

        painter.end()

