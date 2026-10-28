"""AutoGuardian - Hệ thống Giám sát & Bãi đỗ xe Thông minh Real-time.

Application entry point.
"""

from __future__ import annotations

import os
import sys

# Pre-load PyTorch runtime libraries before Qt to prevent DLL initialization conflicts on Windows
import torch
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
    main()
