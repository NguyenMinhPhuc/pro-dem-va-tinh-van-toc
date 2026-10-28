"""Evidence snapshot capture manager for AutoGuardian.

Saves photographic proof of parking violations in standard format:
VIPHAM_[TrackID]_[YYYYMMDD_HHMMSS].jpg
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np


class EvidenceManager:
    """Manages saving and retrieving violation snapshot images."""

    def __init__(self, captures_dir: str = "outputs/captures") -> None:
        """Initializes the EvidenceManager.

        Args:
            captures_dir: Directory where violation images will be stored.
        """
        self.captures_dir = Path(captures_dir)
        self.captures_dir.mkdir(parents=True, exist_ok=True)

    def capture_violation(
        self,
        frame: np.ndarray,
        track_id: int,
        bbox: Optional[Tuple[int, int, int, int]] = None,
        violation_type: str = "PARKING_VIOLATION",
    ) -> Optional[str]:
        """Captures and saves a snapshot of the violating vehicle with an annotated box.

        Args:
            frame: Full BGR video frame.
            track_id: ID of the violating vehicle.
            bbox: (x1, y1, x2, y2) bounding box coordinates of the vehicle.
            violation_type: Type of violation.

        Returns:
            Relative file path string of saved snapshot, or None if failed.
        """
        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"VIPHAM_{track_id}_{timestamp_str}.jpg"
            save_path = self.captures_dir / filename

            # Clone frame to avoid mutating the original stream
            annotated_frame = frame.copy()

            if bbox is not None:
                x1, y1, x2, y2 = bbox
                # Draw thick red violation box
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

                # Add text banner
                banner_text = f"VI PHAM: ID #{track_id} - {violation_type}"
                (tw, th), baseline = cv2.getTextSize(banner_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(
                    annotated_frame,
                    (x1, max(0, y1 - th - 10)),
                    (x1 + tw + 10, y1),
                    (0, 0, 255),
                    -1,
                )
                cv2.putText(
                    annotated_frame,
                    banner_text,
                    (x1 + 5, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            # Write image to disk
            success = cv2.imwrite(str(save_path), annotated_frame)
            if success:
                return str(save_path).replace("\\", "/")
            return None
        except (cv2.error, OSError) as e:
            print(f"[EvidenceManager] Error capturing violation: {e}")
            return None

    def delete_evidence(self, file_path: str) -> bool:
        """Deletes an evidence image file from disk.

        Args:
            file_path: Path to snapshot file.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except OSError as e:
            print(f"[EvidenceManager] Error deleting evidence {file_path}: {e}")
            return False

