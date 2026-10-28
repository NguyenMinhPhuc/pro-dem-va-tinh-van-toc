"""SQLite Database Manager for AutoGuardian.

Provides thread-safe storage for vehicle counting events and parking violations.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseManager:
    """Manages SQLite database storage for event logging and violation records."""

    def __init__(self, db_path: str = "outputs/autoguardian.db") -> None:
        """Initializes the database manager and creates required tables.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a new SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Creates the database schema if tables do not exist."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS vehicle_events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            track_id INTEGER NOT NULL,
                            class_name TEXT NOT NULL,
                            confidence REAL NOT NULL,
                            direction TEXT NOT NULL,
                            license_plate TEXT,
                            speed_kmh REAL,
                            details TEXT
                        );
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS violations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            track_id INTEGER NOT NULL,
                            violation_type TEXT NOT NULL,
                            duration_seconds REAL NOT NULL,
                            license_plate TEXT,
                            speed_kmh REAL,
                            snapshot_path TEXT,
                            details TEXT
                        );
                    """)
                    # Check and migrate columns if opening existing DB
                    cursor.execute("PRAGMA table_info(vehicle_events);")
                    existing_cols = [col[1] for col in cursor.fetchall()]
                    if "license_plate" not in existing_cols:
                        cursor.execute("ALTER TABLE vehicle_events ADD COLUMN license_plate TEXT;")
                    if "speed_kmh" not in existing_cols:
                        cursor.execute("ALTER TABLE vehicle_events ADD COLUMN speed_kmh REAL;")

                    cursor.execute("PRAGMA table_info(violations);")
                    existing_viol_cols = [col[1] for col in cursor.fetchall()]
                    if "license_plate" not in existing_viol_cols:
                        cursor.execute("ALTER TABLE violations ADD COLUMN license_plate TEXT;")
                    if "speed_kmh" not in existing_viol_cols:
                        cursor.execute("ALTER TABLE violations ADD COLUMN speed_kmh REAL;")
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                        ON vehicle_events (timestamp);
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_violations_timestamp 
                        ON violations (timestamp);
                    """)
                    conn.commit()
            except sqlite3.Error as e:
                print(f"[DatabaseManager] Initialization error: {e}")

    def insert_vehicle_event(
        self,
        track_id: int,
        class_name: str,
        confidence: float,
        direction: str = "IN",
        license_plate: Optional[str] = None,
        speed_kmh: Optional[float] = None,
        details: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Optional[int]:
        """Inserts a new vehicle counting event.

        Args:
            track_id: Unique vehicle tracking ID.
            class_name: Detected vehicle class (car, truck, bus, etc.).
            confidence: Detection confidence score (0.0 to 1.0).
            direction: Direction of crossing (e.g., 'IN', 'OUT').
            license_plate: Detected license plate string.
            speed_kmh: Estimated speed in km/h.
            details: Optional extra textual details.
            timestamp: ISO format or YYYY-MM-DD HH:MM:SS string. Defaults to current time.

        Returns:
            The inserted row ID or None on failure.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO vehicle_events (timestamp, track_id, class_name, confidence, direction, license_plate, speed_kmh, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (timestamp, track_id, class_name, float(confidence), direction, license_plate or "", float(speed_kmh) if speed_kmh is not None else 0.0, details or ""),
                    )
                    conn.commit()
                    return cursor.lastrowid
            except sqlite3.Error as e:
                print(f"[DatabaseManager] Error inserting vehicle event: {e}")
                return None

    def insert_violation(
        self,
        track_id: int,
        violation_type: str,
        duration_seconds: float,
        snapshot_path: Optional[str] = None,
        license_plate: Optional[str] = None,
        speed_kmh: Optional[float] = None,
        details: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Optional[int]:
        """Inserts a parking or traffic violation event.

        Args:
            track_id: Unique vehicle tracking ID.
            violation_type: Type of violation (e.g. 'PARKING_TIMEOUT').
            duration_seconds: Dwell time in seconds.
            snapshot_path: Relative or absolute path to the captured evidence image.
            license_plate: Detected license plate string.
            speed_kmh: Estimated speed in km/h.
            details: Optional textual details.
            timestamp: ISO format or YYYY-MM-DD HH:MM:SS string. Defaults to current time.

        Returns:
            The inserted row ID or None on failure.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO violations (timestamp, track_id, violation_type, duration_seconds, license_plate, speed_kmh, snapshot_path, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (timestamp, track_id, violation_type, float(duration_seconds), license_plate or "", float(speed_kmh) if speed_kmh is not None else 0.0, snapshot_path or "", details or ""),
                    )
                    conn.commit()
                    return cursor.lastrowid
            except sqlite3.Error as e:
                print(f"[DatabaseManager] Error inserting violation: {e}")
                return None

    def get_all_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves vehicle counting events ordered by newest first.

        Args:
            limit: Maximum number of rows to return (None for all).

        Returns:
            List of event dictionaries.
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    query = "SELECT * FROM vehicle_events ORDER BY id DESC"
                    if limit is not None:
                        query += f" LIMIT {int(limit)}"
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
            except sqlite3.Error as e:
                print(f"[DatabaseManager] Error querying events: {e}")
                return []

    def get_all_violations(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves violation events ordered by newest first.

        Args:
            limit: Maximum number of rows to return (None for all).

        Returns:
            List of violation dictionaries.
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    query = "SELECT * FROM violations ORDER BY id DESC"
                    if limit is not None:
                        query += f" LIMIT {int(limit)}"
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
            except sqlite3.Error as e:
                print(f"[DatabaseManager] Error querying violations: {e}")
                return []

    def get_total_counts(self) -> Dict[str, int]:
        """Returns aggregate statistics for dashboard display."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM vehicle_events;")
                    total_events = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(DISTINCT track_id) FROM vehicle_events;")
                    unique_vehicles = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM violations;")
                    total_violations = cursor.fetchone()[0]

                    return {
                        "total_events": total_events,
                        "unique_vehicles": unique_vehicles,
                        "total_violations": total_violations,
                    }
            except sqlite3.Error as e:
                print(f"[DatabaseManager] Error getting counts: {e}")
                return {"total_events": 0, "unique_vehicles": 0, "total_violations": 0}

    def clear_all(self) -> bool:
        """Clears all records in tables to support Reset Counter functionality.

        Returns:
            True if cleared successfully, False otherwise.
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM vehicle_events;")
                    cursor.execute("DELETE FROM violations;")
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('vehicle_events', 'violations');")
                    conn.commit()
                    return True
            except sqlite3.Error as e:
                print(f"[DatabaseManager] Error clearing database: {e}")
                return False

