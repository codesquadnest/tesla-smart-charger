"""
Database Controller.

This controller is responsible for interacting with the database to store and
retrieve data.

The controller is implemented as an abstract class that defines the interface
for the controller. This allows for different implementations of the controller
to be used.
"""

from abc import ABC, abstractmethod


class DatabaseController(ABC):
    """Abstract class that defines the interface for the controller."""

    @abstractmethod
    def initialize_db(self) -> None:
        """Initialize the database."""

    @abstractmethod
    def close_connection(self) -> None:
        """Close the connection to the database."""

    @abstractmethod
    def insert_data(self, data: dict) -> None:
        """Insert data into the database."""

    @abstractmethod
    def get_data(self, num_records: int) -> list:
        """Get data from the database."""

    @abstractmethod
    def delete_data(self) -> None:
        """Delete data from the database."""

    @abstractmethod
    def update_data(self, data: dict) -> None:
        """Update data in the database."""


"""Database Controller Factory."""


def create_database_controller(
    implementation_type: str,
    database: str,
    file_path: str,
) -> DatabaseController:
    """Create instances of DatabaseController based on the implementation_type."""
    from tesla_smart_charger.controllers import sqlite_db_controller

    if implementation_type == "sqlite":
        return sqlite_db_controller.SqliteDatabaseController(file_path, database)

    msg = f"Invalid implementation type: {implementation_type}"
    raise ValueError(msg)
