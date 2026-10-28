"""Configuration loader and manager for AutoGuardian.

Provides strongly-typed access to system settings, AI thresholds,
and zone configurations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class AppConfig:
    """Manages application configurations stored in json files."""

    def __init__(self, config_path: str = "configs/config.json", zones_path: str = "configs/zones.json") -> None:
        """Initialize the AppConfig with file paths.

        Args:
            config_path: Relative or absolute path to config.json.
            zones_path: Relative or absolute path to zones.json.
        """
        self.config_path: Path = Path(config_path)
        self.zones_path: Path = Path(zones_path)

        self.config_data: Dict[str, Any] = {}
        self.zones_data: Dict[str, Any] = {}

        self.load_all()

    def load_all(self) -> None:
        """Loads both configuration and zones files with fallback defaults."""
        self.config_data = self._read_json(self.config_path, default=self._default_config())
        self.zones_data = self._read_json(self.zones_path, default=self._default_zones())

    def _read_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        """Safely reads a JSON file or returns default dictionary on failure.

        Args:
            path: Path object to JSON file.
            default: Default dictionary if file cannot be read.

        Returns:
            Dictionary loaded from JSON or fallback default.
        """
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[AppConfig] Warning: Failed to read {path} ({e}). Using default settings.")
            return default

    def save_zones(self) -> bool:
        """Persists current zones data to zones.json.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            self.zones_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.zones_path, "w", encoding="utf-8") as f:
                json.dump(self.zones_data, f, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            print(f"[AppConfig] Error: Failed to save zones to {self.zones_path} ({e})")
            return False

    def save_config(self) -> bool:
        """Persists current config data to config.json.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            print(f"[AppConfig] Error: Failed to save config to {self.config_path} ({e})")
            return False

    # AI properties
    @property
    def model_path(self) -> str:
        return self.config_data.get("ai", {}).get("model_path", "models/yolov8n.pt")

    @property
    def input_size(self) -> tuple[int, int]:
        ai = self.config_data.get("ai", {})
        return (ai.get("input_width", 640), ai.get("input_height", 640))

    @property
    def default_confidence(self) -> float:
        return float(self.config_data.get("ai", {}).get("default_confidence", 0.5))

    @property
    def target_classes(self) -> List[int]:
        return list(self.config_data.get("ai", {}).get("target_classes", [2, 3, 5, 7]))

    # Analytics properties
    @property
    def parking_violation_threshold_seconds(self) -> float:
        return float(self.config_data.get("analytics", {}).get("parking_violation_threshold_seconds", 30.0))

    @property
    def parking_displacement_tolerance(self) -> float:
        return float(self.config_data.get("analytics", {}).get("parking_displacement_tolerance_pixels", 20.0))

    # Speed estimation properties
    @property
    def speed_estimation_enabled(self) -> bool:
        return bool(self.config_data.get("speed_estimation", {}).get("enabled", True))

    @property
    def pixels_per_meter(self) -> float:
        return float(self.config_data.get("speed_estimation", {}).get("pixels_per_meter", 25.0))

    # Plate recognition properties
    @property
    def plate_recognition_enabled(self) -> bool:
        return bool(self.config_data.get("plate_recognition", {}).get("enabled", True))

    @property
    def min_bbox_width_for_plate(self) -> int:
        return int(self.config_data.get("plate_recognition", {}).get("min_bbox_width", 90))

    # Streaming properties
    @property
    def queue_max_size(self) -> int:
        return int(self.config_data.get("streaming", {}).get("queue_max_size", 3))

    @property
    def rtsp_retry_interval_seconds(self) -> float:
        return float(self.config_data.get("streaming", {}).get("rtsp_retry_interval_seconds", 5.0))

    @property
    def loop_video(self) -> bool:
        return bool(self.config_data.get("streaming", {}).get("loop_video", True))

    # Storage properties
    @property
    def db_path(self) -> str:
        return self.config_data.get("storage", {}).get("db_path", "outputs/autoguardian.db")

    @property
    def captures_dir(self) -> str:
        return self.config_data.get("storage", {}).get("captures_dir", "outputs/captures")

    @property
    def reports_dir(self) -> str:
        return self.config_data.get("storage", {}).get("reports_dir", "outputs/reports")

    @property
    def recordings_dir(self) -> str:
        return self.config_data.get("storage", {}).get("recordings_dir", "outputs/recordings")

    # Zones properties
    @property
    def counting_line(self) -> Dict[str, Any]:
        return self.zones_data.get("counting_line", {
            "enabled": True,
            "p1": [100, 360],
            "p2": [1180, 360],
            "name": "Line 1"
        })

    @property
    def parking_roi(self) -> Dict[str, Any]:
        return self.zones_data.get("parking_roi", {
            "enabled": True,
            "points": [[150, 400], [500, 400], [550, 680], [100, 680]],
            "name": "No Parking Zone A",
            "threshold_seconds": 30.0
        })

    @property
    def speed_traps(self) -> Dict[str, Any]:
        """Returns the full speed_traps dictionary or defaults for dual lanes."""
        defaults = self._default_speed_traps()
        st = self.zones_data.get("speed_traps")
        if not isinstance(st, dict):
            legacy = self.zones_data.get("speed_trap")
            if isinstance(legacy, dict):
                defaults["lane_in"] = legacy
                defaults["enabled"] = legacy.get("enabled", True)
            return defaults
        return st

    def _default_speed_traps(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "lane_in": {
                "name": "Làn Vào (IN)",
                "enabled": True,
                "distance_meters": 25.0,
                "line_a": {"p1": [100, 250], "p2": [950, 250], "name": "Mốc A (Vào)"},
                "line_b": {"p1": [100, 750], "p2": [950, 750], "name": "Mốc B (Vào)"},
            },
            "lane_out": {
                "name": "Làn Ra (OUT)",
                "enabled": True,
                "distance_meters": 25.0,
                "line_a": {"p1": [970, 750], "p2": [1820, 750], "name": "Mốc A (Ra)"},
                "line_b": {"p1": [970, 250], "p2": [1820, 250], "name": "Mốc B (Ra)"},
            },
        }

    def get_speed_trap_lane(self, lane_key: str = "in") -> Dict[str, Any]:
        """Returns speed trap zone definition for specified lane ('in' or 'out')."""
        k = "lane_out" if ("out" in str(lane_key).lower() or "ra" in str(lane_key).lower()) else "lane_in"
        traps = self.speed_traps
        lane_data = traps.get(k)
        if isinstance(lane_data, dict) and "line_a" in lane_data and "line_b" in lane_data:
            return lane_data
        return self._default_speed_traps()[k]

    @property
    def speed_trap(self) -> Dict[str, Any]:
        return self.get_speed_trap_lane("in")

    @property
    def speed_trap_enabled(self) -> bool:
        return bool(self.speed_traps.get("enabled", True))

    @property
    def speed_trap_distance(self) -> float:
        return float(self.speed_trap.get("distance_meters", 20.0))

    def update_speed_trap_line_a(self, p1: tuple[int, int], p2: tuple[int, int], lane_key: str = "in") -> None:
        """Updates Speed Trap reference Line A coordinates for specified lane."""
        k = "lane_out" if ("out" in str(lane_key).lower() or "ra" in str(lane_key).lower()) else "lane_in"
        self.zones_data.setdefault("speed_traps", self._default_speed_traps())
        self.zones_data["speed_traps"].setdefault(k, self._default_speed_traps()[k])
        self.zones_data["speed_traps"][k].setdefault("line_a", {})
        self.zones_data["speed_traps"][k]["line_a"]["p1"] = list(p1)
        self.zones_data["speed_traps"][k]["line_a"]["p2"] = list(p2)
        if k == "lane_in":
            self.zones_data.setdefault("speed_trap", {})
            self.zones_data["speed_trap"]["line_a"] = self.zones_data["speed_traps"][k]["line_a"]
        self.save_zones()

    def update_speed_trap_line_b(self, p1: tuple[int, int], p2: tuple[int, int], lane_key: str = "in") -> None:
        """Updates Speed Trap reference Line B coordinates for specified lane."""
        k = "lane_out" if ("out" in str(lane_key).lower() or "ra" in str(lane_key).lower()) else "lane_in"
        self.zones_data.setdefault("speed_traps", self._default_speed_traps())
        self.zones_data["speed_traps"].setdefault(k, self._default_speed_traps()[k])
        self.zones_data["speed_traps"][k].setdefault("line_b", {})
        self.zones_data["speed_traps"][k]["line_b"]["p1"] = list(p1)
        self.zones_data["speed_traps"][k]["line_b"]["p2"] = list(p2)
        if k == "lane_in":
            self.zones_data.setdefault("speed_trap", {})
            self.zones_data["speed_trap"]["line_b"] = self.zones_data["speed_traps"][k]["line_b"]
        self.save_zones()

    def update_speed_trap_distance(self, distance_meters: float, enabled: bool = True, lane_key: str = "in") -> None:
        """Updates Speed Trap physical distance between lines for specified lane."""
        k = "lane_out" if ("out" in str(lane_key).lower() or "ra" in str(lane_key).lower()) else "lane_in"
        self.zones_data.setdefault("speed_traps", self._default_speed_traps())
        self.zones_data["speed_traps"].setdefault(k, self._default_speed_traps()[k])
        self.zones_data["speed_traps"][k]["distance_meters"] = max(1.0, float(distance_meters))
        self.zones_data["speed_traps"][k]["enabled"] = enabled
        if k == "lane_in":
            self.zones_data.setdefault("speed_trap", {})
            self.zones_data["speed_trap"]["distance_meters"] = max(1.0, float(distance_meters))
            self.zones_data["speed_trap"]["enabled"] = enabled
        self.save_zones()

    def reset_speed_traps_to_defaults(self) -> None:
        """Resets both lane speed traps to default values."""
        self.zones_data["speed_traps"] = self._default_speed_traps()
        self.zones_data["speed_trap"] = self._default_speed_traps()["lane_in"]
        self.save_zones()

    def update_counting_line(self, p1: tuple[int, int], p2: tuple[int, int], enabled: bool = True) -> None:
        """Updates virtual counting line coordinates."""
        self.zones_data.setdefault("counting_line", {})
        self.zones_data["counting_line"]["p1"] = list(p1)
        self.zones_data["counting_line"]["p2"] = list(p2)
        self.zones_data["counting_line"]["enabled"] = enabled
        self.save_zones()

    def update_parking_roi(self, points: List[tuple[int, int]], enabled: bool = True) -> None:
        """Updates parking ROI polygon coordinates."""
        self.zones_data.setdefault("parking_roi", {})
        self.zones_data["parking_roi"]["points"] = [list(pt) for pt in points]
        self.zones_data["parking_roi"]["enabled"] = enabled
        self.save_zones()

    def _default_config(self) -> Dict[str, Any]:
        return {
            "system": {"app_name": "AutoGuardian", "version": "1.0.0"},
            "ai": {
                "model_path": "models/yolov8n.pt",
                "input_width": 640,
                "input_height": 640,
                "default_confidence": 0.5,
                "target_classes": [2, 3, 5, 7],
                "target_class_names": ["car", "motorcycle", "bus", "truck"],
                "tracker_type": "bytetrack.yaml"
            },
            "analytics": {
                "parking_violation_threshold_seconds": 30.0,
                "parking_displacement_tolerance_pixels": 20.0,
                "min_track_history": 10
            },
            "streaming": {
                "queue_max_size": 3,
                "rtsp_retry_interval_seconds": 5.0,
                "default_camera_index": 0
            },
            "storage": {
                "db_path": "outputs/autoguardian.db",
                "captures_dir": "outputs/captures",
                "reports_dir": "outputs/reports",
                "recordings_dir": "outputs/recordings"
            },
            "ui": {
                "show_bbox": True,
                "show_track_id": True,
                "show_fps": True,
                "show_counting_line": True,
                "show_parking_roi": True,
                "sound_alert_enabled": True,
                "popup_alert_enabled": True
            }
        }

    def _default_zones(self) -> Dict[str, Any]:
        return {
            "counting_line": {
                "enabled": True,
                "p1": [100, 360],
                "p2": [1180, 360],
                "name": "Line 1"
            },
            "parking_roi": {
                "enabled": True,
                "points": [[150, 400], [500, 400], [550, 680], [100, 680]],
                "name": "No Parking Zone A",
                "threshold_seconds": 30.0
            },
            "speed_traps": self._default_speed_traps()
        }

