"""
SQLite DB Controller

Stores and retrieves overload event records.
Supports schema migration to add the vehicle_id column introduced in v2.
"""

import sqlite3

from tesla_smart_charger import logger
from tesla_smart_charger.controllers.db_controller import DatabaseController

tsc_logger = logger.get_logger()


class SqliteDatabaseController(DatabaseController):
    """SQLite-backed implementation of DatabaseController."""

    def __init__(self, file_path: str, database: str) -> None:
        self.type = "sqlite"
        self.file_path = file_path
        self.database = database
        self.connection = None
        self.cursor = None

    def initialize_db(self) -> None:
        """Open the database and create / migrate the schema."""
        if self.connection is not None:
            tsc_logger.warning("Database connection already initialised.")
            return
        try:
            self.connection = sqlite3.connect(self.file_path)
            self.connection.row_factory = sqlite3.Row  # named-column access
            self.cursor = self.connection.cursor()
            tsc_logger.debug("Connected to SQLite: %s", self.file_path)

            # Create table if it does not exist (original schema)
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS overloads (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    start     TEXT NOT NULL,
                    end       TEXT,
                    duration  INTEGER,
                    vehicle_id TEXT DEFAULT ''
                )
                """
            )
            self.connection.commit()

            # Migrate: add vehicle_id column if missing (databases created before v2)
            existing_cols = {
                row[1]
                for row in self.cursor.execute("PRAGMA table_info(overloads)")
            }
            if "vehicle_id" not in existing_cols:
                tsc_logger.info("Migrating overloads table: adding vehicle_id column.")
                self.cursor.execute(
                    "ALTER TABLE overloads ADD COLUMN vehicle_id TEXT DEFAULT ''"
                )
                self.connection.commit()

        except sqlite3.Error as exc:
            tsc_logger.error("SQLite init error: %s", exc)
            raise

    def close_connection(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            tsc_logger.debug("SQLite connection closed.")

    def insert_data(self, data: dict) -> None:
        """
        Insert an overload event record.

        Expected keys: start, end, duration, vehicle_id (optional).
        """
        try:
            self._ensure_open()
            self.cursor.execute(
                """
                INSERT INTO overloads (start, end, duration, vehicle_id)
                VALUES (:start, :end, :duration, :vehicle_id)
                """,
                {
                    "start": data.get("start", ""),
                    "end": data.get("end", ""),
                    "duration": data.get("duration", 0),
                    "vehicle_id": data.get("vehicle_id", ""),
                },
            )
            self.connection.commit()
            tsc_logger.info("Overload event inserted.")
        except sqlite3.Error as exc:
            tsc_logger.error("SQLite insert error: %s", exc)
            raise

    def get_data(self, num_records: int = 10) -> list:
        """
        Return the most recent *num_records* overload events as dicts.
        """
        try:
            self._ensure_open()
            self.cursor.execute(
                """
                SELECT id, start, end, duration, vehicle_id
                FROM overloads
                ORDER BY id DESC
                LIMIT ?
                """,
                (num_records,),
            )
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            tsc_logger.error("SQLite query error: %s", exc)
            raise

    def get_data_filtered(
        self,
        num_records: int = 100,
        vehicle_id: str = "",
        from_date: str = "",
        to_date: str = "",
    ) -> list:
        """
        Return filtered overload events.

        Parameters
        ----------
        num_records : int
            Maximum number of records to return.
        vehicle_id : str
            If non-empty, filter to this vehicle only.
        from_date : str
            Inclusive lower bound (``YYYY-MM-DD HH:MM:SS``).
        to_date : str
            Inclusive upper bound (``YYYY-MM-DD HH:MM:SS``).
        """
        try:
            self._ensure_open()
            conditions = []
            params: list = []

            if vehicle_id:
                conditions.append("vehicle_id = ?")
                params.append(vehicle_id)
            if from_date:
                conditions.append("start >= ?")
                params.append(from_date)
            if to_date:
                conditions.append("start <= ?")
                params.append(to_date)

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(num_records)

            self.cursor.execute(
                f"""
                SELECT id, start, end, duration, vehicle_id
                FROM overloads
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            )
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            tsc_logger.error("SQLite filtered query error: %s", exc)
            raise

    def delete_data(self) -> None:
        """Delete all overload records."""
        try:
            self._ensure_open()
            self.cursor.execute("DELETE FROM overloads")
            self.connection.commit()
            tsc_logger.info("All overload records deleted.")
        except sqlite3.Error as exc:
            tsc_logger.error("SQLite delete error: %s", exc)
            raise

    def update_data(self, data: dict) -> None:
        """Update the end/duration of an existing record by id."""
        try:
            self._ensure_open()
            self.cursor.execute(
                """
                UPDATE overloads
                SET end = :end, duration = :duration
                WHERE id = :id
                """,
                data,
            )
            self.connection.commit()
        except sqlite3.Error as exc:
            tsc_logger.error("SQLite update error: %s", exc)
            raise

    # ─── Internal helpers ──────────────────────────────────────────────────────

    def _ensure_open(self) -> None:
        if self.connection is None or self.cursor is None:
            self.initialize_db()
