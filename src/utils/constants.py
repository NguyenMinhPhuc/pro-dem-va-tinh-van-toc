"""Global constants and color palettes for AutoGuardian.

Eliminates magic numbers across detection, tracking, drawing and GUI.
"""

from typing import Tuple

# Frame & Dimension Constants
DEFAULT_FRAME_WIDTH: int = 1280
DEFAULT_FRAME_HEIGHT: int = 720
MODEL_INPUT_WIDTH: int = 640
MODEL_INPUT_HEIGHT: int = 640

# Color Constants (BGR format for OpenCV)
COLOR_GREEN: Tuple[int, int, int] = (0, 255, 0)
COLOR_RED: Tuple[int, int, int] = (0, 0, 255)
COLOR_YELLOW: Tuple[int, int, int] = (0, 255, 255)
COLOR_BLUE: Tuple[int, int, int] = (255, 0, 0)
COLOR_CYAN: Tuple[int, int, int] = (255, 255, 0)
COLOR_ORANGE: Tuple[int, int, int] = (0, 165, 255)
COLOR_WHITE: Tuple[int, int, int] = (255, 255, 255)
COLOR_BLACK: Tuple[int, int, int] = (0, 0, 0)

# Line & Drawing Thickness
DEFAULT_LINE_THICKNESS: int = 2
DEFAULT_BOX_THICKNESS: int = 2
DEFAULT_FONT_SCALE: float = 0.55
DEFAULT_FONT_THICKNESS: int = 1

# Detection & Tracking Defaults
DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5
MAX_LOST_TRACK_FRAMES: int = 30

# Parking Analytics Defaults
DEFAULT_PARKING_TIME_LIMIT_SECONDS: float = 30.0
DEFAULT_PARKING_DISPLACEMENT_LIMIT_PIXELS: float = 20.0

# Streaming & Queue Defaults
FRAME_QUEUE_MAX_SIZE: int = 3
RTSP_RECONNECT_INTERVAL_SECONDS: float = 5.0
FPS_CALCULATION_WINDOW: int = 30

# Database & Storage
EVENT_TYPE_COUNT: str = "VEHICLE_COUNT"
EVENT_TYPE_PARKING_VIOLATION: str = "PARKING_VIOLATION"

# Default Speed Trap Zones for Dual Lanes (Lane IN & Lane OUT)
DEFAULT_TRAP_IN_LINE_A: Tuple[Tuple[int, int], Tuple[int, int]] = ((100, 250), (950, 250))
DEFAULT_TRAP_IN_LINE_B: Tuple[Tuple[int, int], Tuple[int, int]] = ((100, 750), (950, 750))
DEFAULT_TRAP_IN_DISTANCE: float = 25.0

DEFAULT_TRAP_OUT_LINE_A: Tuple[Tuple[int, int], Tuple[int, int]] = ((970, 750), (1820, 750))
DEFAULT_TRAP_OUT_LINE_B: Tuple[Tuple[int, int], Tuple[int, int]] = ((970, 250), (1820, 250))
DEFAULT_TRAP_OUT_DISTANCE: float = 25.0

