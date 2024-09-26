"""
SQLite DB Controller

This controller is responsible for interacting with an SQLite database to store and
retrieve data.
"""

import sqlite3

from tesla_smart_charger import logger
from tesla_smart_charger.controllers.db_controller import DatabaseController

# Set up logging
tsc_logger = logger.get_logger()


class SqliteDatabaseController(DatabaseController):
    """Implementation of the SQLite database controller."""

    def __init__(self, file_path: str, database: str) -> None:
        """
        Initialize the SQLite database controller.

        Args:
            file_path (str): The path to the SQLite database file.
            database (str): The name of the database.
        """
        self.type = "sqlite"
        self.file_path = file_path
        self.database = database
        self.connection = None
        self.cursor = None

    def initialize_db(self) -> None:
        """Initialize the database."""
        if self.connection is not None:
            tsc_logger.warning("Database connection already initialized")
            return
        try:
            self.connection = sqlite3.connect(self.file_path)
            self.cursor = self.connection.cursor()
            tsc_logger.info(f"Connected to SQLite database: {self.file_path}")

            # Create the tables if they do not exist
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS overloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start TEXT NOT NULL,
                    end TEXT,
                    duration INTEGER
                )
                """
            )
            self.connection.commit()
            tsc_logger.info("Created table: overloads")

        except sqlite3.Error as e:
            tsc_logger.error(f"Error connecting to SQLite database: {e}")
            raise e

    def close_connection(self) -> None:
        """Close the connection to the database."""
        if self.connection:
            self.connection.close()
            tsc_logger.info("Closed connection to SQLite database")

    def insert_data(self, data: dict) -> None:
        """
        Insert data into the database.

        Args:
            data (dict): The data to insert into the database.
        """
        try:
            self.cursor.execute(
                """
                INSERT INTO overloads (start, end, duration)
                VALUES (:start, :end, :duration)
                """,
                data,
            )
            self.connection.commit()
            tsc_logger.info("Data inserted into table: overloads")

        except sqlite3.Error as e:
            tsc_logger.error(f"Error inserting data into SQLite database: {e}")
            raise e

    def get_data(self, num_records: int = 10) -> list:
        """
        Get data from the database.

        Args:
            num_records (int): The number of records to retrieve from the database.

        Returns:
            list: The data retrieved from the database.
        """
        try:
            self.cursor.execute(
                """
                SELECT * FROM overloads
                ORDER BY id DESC
                LIMIT ?
                """, (num_records,)
            )
            data = self.cursor.fetchall()
            tsc_logger.info("Data retrieved from table: overloads")
            return data

        except sqlite3.Error as e:
            tsc_logger.error(f"Error getting data from SQLite database: {e}")
            raise e

    def delete_data(self) -> None:
        """Delete data from the database."""
        try:
            self.cursor.execute(
                """
                DELETE FROM overloads
                """
            )
            self.connection.commit()
            tsc_logger.info("Data deleted from table: overloads")

        except sqlite3.Error as e:
            tsc_logger.error(f"Error deleting data from SQLite database: {e}")
            raise e

    def update_data(self, data: dict) -> None:
        """
        Update data in the database.

        Args:
            data (dict): The data to update in the database.
        """
        try:
            self.cursor.execute(
                """
                UPDATE overloads
                SET end = :end, duration = :duration
                WHERE id = :id
                """,
                data,
            )
            self.connection.commit()
            tsc_logger.info("Data updated in table: overloads")

        except sqlite3.Error as e:
            tsc_logger.error(f"Error updating data in SQLite database: {e}")
            raise e
