"""AutoGuardian - Hệ thống Giám sát & Bãi đỗ xe Thông minh Real-time.

Application entry point.
"""

from __future__ import annotations

import multiprocessing
import os
import sys


def _prepare_frozen_runtime() -> None:
    """Packaged .exe: run from the exe folder, where configs/, models/ and outputs/ live.

    A windowed exe has no console (sys.stdout/stderr are None), so logs go to a file.
    Must run before importing torch/ultralytics, which bind their loggers to stdout.
    """
    if not getattr(sys, "frozen", False):
        return
    os.chdir(os.path.dirname(sys.executable))
    if sys.stdout is None or sys.stderr is None:
        os.makedirs("outputs/logs", exist_ok=True)
        log_file = open("outputs/logs/autoguardian.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log_file
        sys.stderr = sys.stderr or log_file


_prepare_frozen_runtime()

# No network traffic from the app itself: disable Ultralytics usage analytics and online checks
# (the model is bundled). Only video sources chosen by the user (e.g. RTSP cameras) are contacted.
os.environ.setdefault("YOLO_OFFLINE", "1")

# Pre-load PyTorch and ONNX Runtime libraries before Qt: PyQt5 ships an old MSVC runtime
# (msvcp140 14.26) that crashes recent onnxruntime builds if it is loaded first on Windows
import torch
import onnxruntime  # noqa: F401
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def main() -> None:
    """Entry point function initializing QApplication and MainWindow."""
    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("AutoGuardian")
    app.setOrganizationName("AutoGuardian Team")

    window = MainWindow(config_path="configs/config.json")
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
