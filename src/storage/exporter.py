"""Report Exporter for AutoGuardian.

Exports vehicle counting events and parking violation records to Excel (.xlsx) and CSV (.csv).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd

from src.storage.database import DatabaseManager


class ReportExporter:
    """Handles exporting event records from SQLite database to Excel and CSV files."""

    def __init__(self, db_manager: DatabaseManager, default_reports_dir: str = "outputs/reports") -> None:
        """Initializes the ReportExporter.

        Args:
            db_manager: Instance of DatabaseManager.
            default_reports_dir: Default directory for exported files.
        """
        self.db = db_manager
        self.reports_dir = Path(default_reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def export_to_excel(self, output_path: Optional[str] = None) -> Optional[str]:
        """Exports both vehicle counting events and violations to a multi-sheet Excel workbook.

        Args:
            output_path: Optional custom file path. If None, auto-generates timestamped filename.

        Returns:
            The path of the exported Excel file or None on failure.
        """
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = self.reports_dir / f"BAO_CAO_AUTOGUARDIAN_{timestamp}.xlsx"
            else:
                target_path = Path(output_path)

            target_path.parent.mkdir(parents=True, exist_ok=True)

            events = self.db.get_all_events()
            violations = self.db.get_all_violations()

            # Prepare Events DataFrame
            if events:
                df_events = pd.DataFrame(events)
                df_events.rename(
                    columns={
                        "id": "STT",
                        "timestamp": "Thời gian",
                        "track_id": "Mã xe (Track ID)",
                        "license_plate": "Biển số xe",
                        "speed_kmh": "Tốc độ (km/h)",
                        "class_name": "Loại phương tiện",
                        "confidence": "Độ tin cậy",
                        "direction": "Hướng di chuyển",
                        "details": "Ghi chú",
                    },
                    inplace=True,
                )
            else:
                df_events = pd.DataFrame(
                    columns=["STT", "Thời gian", "Mã xe (Track ID)", "Biển số xe", "Tốc độ (km/h)", "Loại phương tiện", "Độ tin cậy", "Hướng di chuyển", "Ghi chú"]
                )

            # Prepare Violations DataFrame
            if violations:
                df_violations = pd.DataFrame(violations)
                df_violations.rename(
                    columns={
                        "id": "STT",
                        "timestamp": "Thời gian vi phạm",
                        "track_id": "Mã xe (Track ID)",
                        "license_plate": "Biển số xe",
                        "speed_kmh": "Tốc độ (km/h)",
                        "violation_type": "Hành vi vi phạm",
                        "duration_seconds": "Thời gian đỗ (giây)",
                        "snapshot_path": "Đường dẫn ảnh bằng chứng",
                        "details": "Ghi chú",
                    },
                    inplace=True,
                )
            else:
                df_violations = pd.DataFrame(
                    columns=["STT", "Thời gian vi phạm", "Mã xe (Track ID)", "Biển số xe", "Tốc độ (km/h)", "Hành vi vi phạm", "Thời gian đỗ (giây)", "Đường dẫn ảnh bằng chứng", "Ghi chú"]
                )

            # Write to Excel with multiple sheets
            with pd.ExcelWriter(str(target_path), engine="openpyxl") as writer:
                df_events.to_excel(writer, sheet_name="Lưu lượng xe đếm", index=False)
                df_violations.to_excel(writer, sheet_name="Sự kiện vi phạm", index=False)

            return str(target_path).replace("\\", "/")
        except (OSError, ValueError, KeyError) as e:
            print(f"[ReportExporter] Error exporting to Excel: {e}")
            return None

    def export_to_csv(self, output_path: Optional[str] = None) -> Optional[str]:
        """Exports vehicle counting events to a CSV file.

        Args:
            output_path: Optional custom file path. If None, auto-generates timestamped filename.

        Returns:
            The path of the exported CSV file or None on failure.
        """
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = self.reports_dir / f"BAO_CAO_LUU_LUONG_{timestamp}.csv"
            else:
                target_path = Path(output_path)

            target_path.parent.mkdir(parents=True, exist_ok=True)

            events = self.db.get_all_events()
            if events:
                df_events = pd.DataFrame(events)
                df_events.rename(
                    columns={
                        "id": "STT",
                        "timestamp": "Timestamp",
                        "track_id": "Track ID",
                        "license_plate": "License Plate",
                        "speed_kmh": "Speed (km/h)",
                        "class_name": "Class",
                        "confidence": "Confidence",
                        "direction": "Direction",
                        "details": "Details",
                    },
                    inplace=True,
                )
            else:
                df_events = pd.DataFrame(
                    columns=["STT", "Timestamp", "Track ID", "License Plate", "Speed (km/h)", "Class", "Confidence", "Direction", "Details"]
                )

            df_events.to_csv(str(target_path), index=False, encoding="utf-8-sig")
            return str(target_path).replace("\\", "/")
        except (OSError, ValueError) as e:
            print(f"[ReportExporter] Error exporting to CSV: {e}")
            return None

