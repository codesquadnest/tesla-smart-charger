"""Handles the overload of the charger."""

import time
from fastapi import HTTPException

from tesla_smart_charger import constants, logger
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.controllers import db_controller as db
from tesla_smart_charger.controllers import em_controller as _em_controller
from tesla_smart_charger.tesla_api import TeslaAPI

# Set up logging
tsc_logger = logger.get_logger()

db_controller = None
tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()
tesla_api = TeslaAPI(tesla_config)

# Constants
SLEEP_TIME = round(float(tesla_config.config["sleepTimeSecs"]))
HOME_MAX_AMPS = float(tesla_config.config["homeMaxAmps"])
CHARGER_MAX_AMPS = float(tesla_config.config["chargerMaxAmps"])
CHARGER_MIN_AMPS = float(tesla_config.config["chargerMinAmps"])
MAX_TESLA_API_QUERIES = round(float(constants.MAX_QUERIES))


def __init_db_controller():
    """Initialize the database controller."""
    global db_controller
    db_controller = db.create_database_controller(
        constants.DB_TYPE, constants.DB_NAME, constants.DB_FILE_PATH
    )
    db_controller.initialize_db()


def _reload_config() -> None:
    """Reload the config."""
    tesla_config.load_config()
    tesla_api.charger_config = tesla_config


def _calculate_new_charge_limit(
    current_charge_limit: float,
    current_em_consumption: float,
    max_charge_limit: float,
    min_charge_limit: float,
    home_max_amps: float,
) -> int:
    """
    Calculate the new charge limit.

    Based on the current charge limit and the current consumption of the house.
    """
    consumption_difference = current_em_consumption - home_max_amps

    # Adjust the charge limit based on the consumption difference
    new_charge_limit = current_charge_limit - consumption_difference

    if new_charge_limit > max_charge_limit:
        new_charge_limit = max_charge_limit
    elif new_charge_limit < min_charge_limit:
        new_charge_limit = min_charge_limit

    tsc_logger.debug(
        f"New calculated charge limit: {new_charge_limit}A "
        f"(current charge limit: {current_charge_limit}A, "
        f"consumption difference: {consumption_difference:.2f}A)"
    )

    return round(float(new_charge_limit))


def _get_current_consumption_in_amps(em_controller) -> float:
    """Get the current consumption of the house in amps."""
    try:
        current_em_consumption = em_controller.get_consumption() / 230
        tsc_logger.debug(f"Current consumption in amps: {current_em_consumption:.2f}")
    except ValueError as e:
        tsc_logger.error(f"Error getting consumption: {e}")
        return None


def _finish_overload_handling(start_time: str) -> None:
    """Finish the overload handling."""
    # Initialize the database controller
    __init_db_controller()

    # Save end time of the overload (yyyy-mm-dd HH:MM:SS) as a string
    end_time = time.strftime("%Y-%m-%d %H:%M:%S")
    overload_data = {"start": start_time, "end": end_time}

    # Calculate the duration of the overload in seconds
    try:
        start_time_obj = time.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_time_obj = time.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        duration = time.mktime(end_time_obj) - time.mktime(start_time_obj)
        overload_data["duration"] = duration
    except ValueError as e:
        tsc_logger.error(f"Error calculating overload duration: {e}")
        overload_data["duration"] = 0

    # Insert the overload data into the database
    try:
        db_controller.insert_data(overload_data)
        tsc_logger.info("Overload data saved to database")
    except Exception as e:
        tsc_logger.error(f"Error saving overload data to database: {e}")
    finally:
        db_controller.close_connection()


def handle_overload() -> None:
    """Handle the overload of the charger."""
    tsc_logger.info("Handling overload! Supervised session started.")
    tesla_api_calls = 0

    # Save start time of the overload (yyyy-mm-dd HH:MM:SS) as a string
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")

    # Instantiate the Energy Monitor controller
    try:
        em_controller = _em_controller.create_energy_monitor_controller(
            tesla_config.config["energyMonitorType"],
            tesla_config.config["energyMonitorIp"],
        )
    except ValueError:
        tsc_logger.error("Invalid energy monitor type")
        tsc_logger.info("Supervised session ended.")
        return

    # Sleep for a longer time so the power consumption can stabilize after the overload
    # while still checks if the house is consuming more power than the limit
    for _ in range(10):
        time.sleep(SLEEP_TIME)
        _reload_config()
        current_em_consumption_amps = _get_current_consumption_in_amps(em_controller)
        if current_em_consumption_amps > HOME_MAX_AMPS:
            tsc_logger.info("Overload still present... starting stabilization")
            break

    # Stabilize the power consumption after the overload
    try:
        _reload_config()
        vehicle_data = tesla_api.get_vehicle_data()
    except HTTPException as e:
        tsc_logger.error(f"Supervised session interrupted! {e}")
        return

    charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]

    while (
        vehicle_data["state"] == "online"
        and vehicle_data["charge_state"]["charging_state"] == "Charging"
        and tesla_api_calls < MAX_TESLA_API_QUERIES
        and round(float(charger_actual_current))
        < round(float(tesla_config.config["chargerMaxAmps"]))
    ):
        _reload_config()

        # Get the current charge limit in amps
        charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]

        # Get the current consumption of the house in amps
        current_em_consumption_amps = _get_current_consumption_in_amps(em_controller)
        if current_em_consumption_amps is None:
            tsc_logger.info("Supervised session ended.")
            return

        # Calculate the new charge limit
        new_charge_limit = _calculate_new_charge_limit(
            float(charger_actual_current),
            float(current_em_consumption_amps),
            CHARGER_MAX_AMPS,
            CHARGER_MIN_AMPS,
            HOME_MAX_AMPS,
        )

        if round(float(new_charge_limit)) != round(float(charger_actual_current)):
            tsc_logger.info(f"Setting new charge limit: {new_charge_limit}A")
            # Set the new charge limit
            try:
                tesla_api.set_charge_amp_limit(new_charge_limit)
            except HTTPException as e:
                tsc_logger.error(f"Supervised session interrupted! {e}")
                return
            tesla_api_calls = 0
        else:
            tsc_logger.info("No change in charge limit")
            if round(float(charger_actual_current)) == round(
                float(tesla_config.config["chargerMaxAmps"])
            ):
                tesla_api_calls += 1

        # Sleep for the configured time
        time.sleep(SLEEP_TIME)

        # Get the current vehicle data
        try:
            vehicle_data = tesla_api.get_vehicle_data()
        except HTTPException as e:
            tsc_logger.error(f"Supervised session interrupted! {e}")
            return

    _finish_overload_handling(start_time)
    tsc_logger.info("Overload handled! Supervised session ended.")
