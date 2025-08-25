"""Handles the overload of the charger."""

import time
from fastapi import HTTPException

from tesla_smart_charger import constants, logger
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.controllers import db_controller
from tesla_smart_charger.controllers import em_controller as _em_controller
from tesla_smart_charger.tesla_api import TeslaAPI

# Set up logging
tsc_logger = logger.get_logger()

controller_db = None
tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()


tesla_api = TeslaAPI(tesla_config)


def _init_db_controller():
    """Initialize the database controller."""
    global controller_db
    controller_db = db_controller.create_database_controller(
        constants.DB_TYPE, constants.DB_NAME, constants.DB_FILE_PATH
    )
    if not controller_db:
        tsc_logger.error("Failed to create database controller.")


def _finish_overload_handling(start_time: str) -> None:
    """Finish the overload handling."""
    # Initialize the database controller
    try:
        _init_db_controller()
    except Exception as e:
        tsc_logger.error("Database controller initialization failed: %s", e)
        tsc_logger.info("Supervised session ended.")
        return

    # Save end time of the overload (yyyy-mm-dd HH:MM:SS) as a string
    end_time = time.strftime("%Y-%m-%d %H:%M:%S")
    overload_data = {"start": start_time, "end": end_time}

    # Calculate the duration of the overload in seconds
    try:
        start_time_obj = time.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_time_obj = time.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        duration = time.mktime(end_time_obj) - time.mktime(start_time_obj)
        overload_data["duration"] = str(duration)
    except ValueError as e:
        tsc_logger.error(f"Error calculating overload duration: {e}")
        overload_data["duration"] = "0"

    # Insert the overload data into the database
    if controller_db:
        try:
            controller_db.insert_data(overload_data)
            tsc_logger.info("Overload data saved to database")
        except Exception as e:
            tsc_logger.error("Error saving overload data to database: %s", e)
        finally:
            try:
                controller_db.close_connection()
            except Exception as e:
                tsc_logger.warning("Error closing database connection: %s", e)
    else:
        tsc_logger.warning(
            "Skipping data insertion and connection close: controller_db is not initialized."
        )


def _reload_config() -> None:
    """Reload the config."""
    tesla_config.load_config()
    cfg = tesla_config.get_config()
    if "error" in cfg:
        msg = f"Config not loaded: {cfg['error']}"
        tsc_logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)
    tesla_api.charger_config = tesla_config
    tesla_api.http_proxy = cfg.get("teslaHttpProxy") or ""


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
        return 0.0
    return current_em_consumption


def handle_overload() -> None:
    """Handle the overload of the charger."""
    tsc_logger.info("Handling overload! Supervised session started.")
    tesla_api_calls = 0

    # Save start time of the overload (yyyy-mm-dd HH:MM:SS) as a string
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")

    # Instantiate the Energy Monitor controller
    cfg = tesla_config.get_config()
    if "error" in cfg:
        tsc_logger.error(f"Failed to load configuration: {cfg['error']}")
        tsc_logger.info("Supervised session ended.")
        return
    try:
        em_controller = _em_controller.create_energy_monitor_controller(
            cfg["energyMonitorType"],
            cfg["energyMonitorIp"],
        )
    except ValueError:
        tsc_logger.error("Invalid energy monitor type")
        tsc_logger.info("Supervised session ended.")
        return

    # Sleep for a longer time so the power consumption can stabilize after the overload
    # while still checks if the house is consuming more power than the limit
    for _ in range(10):
        time.sleep(round(float(cfg["sleepTimeSecs"])))
        _reload_config()
        current_em_consumption_amps = _get_current_consumption_in_amps(em_controller)
        if current_em_consumption_amps > float(cfg["homeMaxAmps"]):
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

    while True:
        # Always act on fresh config and telemetry
        try:
            _reload_config()
            cfg = tesla_config.get_config()
            vehicle_data = tesla_api.get_vehicle_data()
        except HTTPException as e:
            tsc_logger.error(f"Supervised session interrupted! {e}")
            return
        # Current charge limit in amps from fresh data
        charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]
        # Check loop continuation conditions using fresh cfg
        if not (
            vehicle_data["state"] == "online"
            and vehicle_data["charge_state"]["charging_state"] == "Charging"
            and tesla_api_calls < int(constants.MAX_QUERIES)
            and round(float(charger_actual_current))
            < round(float(cfg["chargerMaxAmps"]))
        ):
            break
        _reload_config()

        # Get the current charge limit in amps
        charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]

        # Get the current consumption of the house in amps
        current_em_consumption_amps = _get_current_consumption_in_amps(em_controller)
        if current_em_consumption_amps == 0.0:
            tsc_logger.info("Supervised session ended.")
            return

        # Calculate the new charge limit
        new_charge_limit = _calculate_new_charge_limit(
            float(charger_actual_current),
            float(current_em_consumption_amps),
            float(cfg["chargerMaxAmps"]),
            float(cfg["chargerMinAmps"]),
            float(cfg["homeMaxAmps"]),
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
                float(cfg["chargerMaxAmps"])
            ):
                tesla_api_calls += 1

        # Sleep for the configured time
        time.sleep(round(float(cfg["sleepTimeSecs"])))

        # Get the current vehicle data
        try:
            vehicle_data = tesla_api.get_vehicle_data()
        except HTTPException as e:
            tsc_logger.error(f"Supervised session interrupted! {e}")
            return

    _finish_overload_handling(start_time)
    tsc_logger.info("Overload handled! Supervised session ended.")
