"""Handles the overload of the charger."""

import time
from fastapi import HTTPException

from tesla_smart_charger import constants, logger
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.controllers import em_controller as _em_controller
from tesla_smart_charger.tesla_api import TeslaAPI

# Set up logging
tsc_logger = logger.get_logger()

tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()
tesla_api = TeslaAPI(tesla_config)


def _reload_config() -> None:
    """Reload the config."""
    tesla_config.load_config()
    tesla_api.charger_config = tesla_config
    tsc_logger.info("Configuration reloaded")


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

    return int(new_charge_limit)


def handle_overload() -> None:
    """Handle the overload of the charger."""
    tsc_logger.info("Handling overload! Supervised session started.")
    tesla_api_calls = 0

    # Instantiate the Energy Monitor controller
    try:
        em_controller = _em_controller.create_energy_monitor_controller(
            tesla_config.config["energyMonitorType"],
            tesla_config.config["energyMonitorIp"],
        )
    except ValueError as e:
        tsc_logger.error("Invalid energy monitor type")
        tsc_logger.info("Supervised session ended.")
        raise HTTPException(
            status_code=500,
            detail="Invalid energy monitor type",
        ) from e

    # Sleep for the configured time
    time.sleep(int(tesla_config.config["sleepTimeSecs"]))

    # Get the current vehicle data
    try:
        _reload_config()
        vehicle_data = tesla_api.get_vehicle_data()
    except HTTPException as e:
        tsc_logger.error("Supervised session interrupted!")
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Request failed: {e}",
        ) from e

    charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]

    while (
        vehicle_data["state"] == "online"
        and vehicle_data["charge_state"]["charging_state"] == "Charging"
        and tesla_api_calls < int(constants.MAX_QUERIES)
    ):
        _reload_config()

        # Get the current charge limit in amps
        charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]

        # Get the current consumption of the house in kW and convert to amps
        current_em_consumption = em_controller.get_consumption() / 1000
        current_em_consumption_amps = current_em_consumption * 1000 / 230

        tsc_logger.info(
            f"Current charge limit: {charger_actual_current}A, "
            f"current house consumption: {current_em_consumption:.2f}kW "
            f"({current_em_consumption_amps:.2f}A)"
        )

        # Calculate the new charge limit
        new_charge_limit = _calculate_new_charge_limit(
            float(charger_actual_current),
            float(current_em_consumption_amps),
            float(tesla_config.config["chargerMaxAmps"]),
            float(tesla_config.config["chargerMinAmps"]),
            float(tesla_config.config["homeMaxAmps"]),
        )

        if int(new_charge_limit) != int(charger_actual_current):
            tsc_logger.info(f"Setting new charge limit: {new_charge_limit}A")
            # Set the new charge limit
            try:
                tesla_api.set_charge_amp_limit(new_charge_limit)
            except HTTPException as e:
                tsc_logger.error("Supervised session interrupted!")
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"Request failed: {e}",
                ) from e
            tesla_api_calls = 0
        else:
            tsc_logger.info("No change in charge limit")
            if int(charger_actual_current) == int(
                tesla_config.config["chargerMaxAmps"]
            ):
                tesla_api_calls += 1

        # Sleep for the configured time
        time.sleep(int(tesla_config.config["sleepTimeSecs"]))

        # Get the current vehicle data
        try:
            vehicle_data = tesla_api.get_vehicle_data()
        except HTTPException as e:
            tsc_logger.error("Supervised session interrupted!")
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Request failed: {e}",
            ) from e

    tsc_logger.info("Overload handled! Supervised session ended.")
