"""Handles the overload of the charger."""

import time

from fastapi import HTTPException

from tesla_smart_charger import constants
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.controllers import em_controller as _em_controller
from tesla_smart_charger.tesla_api import TeslaAPI

tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()
tesla_api = TeslaAPI(tesla_config)


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

    return int(new_charge_limit)


def handle_overload() -> None:
    """Handle the overload of the charger."""
    print("Handling overload!")
    print("Supervised session started!")
    # Instantiate the Energy Monitor controller
    try:
        em_controller = _em_controller.create_energy_monitor_controller(
            tesla_config.config["energyMonitorType"],
            tesla_config.config["energyMonitorIp"],
        )
    except ValueError as e:
        print("Invalid energy monitor type")
        print("Supervised session ended!")
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
        print("Supervised session interrupted!")
        raise HTTPException(
            status_code=e.status_code, detail=f"Request failed: {e!s}",
        ) from e

    while (
        vehicle_data["state"] == "online"
        and vehicle_data["charge_state"]["charging_state"] == "Charging"
    ):
        _reload_config()
        # Get the current charge limit in amps
        charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]

        # Get the current consumption of the house in kW
        current_em_consumption = em_controller.get_consumption() / 1000

        # Convert the current consumption to amps
        current_em_consumption_amps = current_em_consumption * 1000 / 230

        print(
            f"Current charge limit: {charger_actual_current}A, "
            f"current house consumption: {current_em_consumption}kW, "
            f"current house consumption: {current_em_consumption_amps}A",
        )

        # Calculate the new charge limit
        new_charge_limit = _calculate_new_charge_limit(
            float(charger_actual_current),
            float(current_em_consumption_amps),
            float(tesla_config.config["chargerMaxAmps"]),
            float(tesla_config.config["chargerMinAmps"]),
            float(tesla_config.config["homeMaxAmps"]),
        )

        print(f"New charge limit: {new_charge_limit}A")
        if new_charge_limit != charger_actual_current:
            # Set the new charge limit
            try:
                tesla_api.set_charge_amp_limit(new_charge_limit)
            except HTTPException as e:
                print("Supervised session interrupted!")
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"Request failed: {e!s}",
                ) from e
        else:
            print("No change in charge limit")

        # Sleep for the configured time
        time.sleep(int(tesla_config.config["sleepTimeSecs"]))

        # Get the current vehicle data
        try:
            vehicle_data = tesla_api.get_vehicle_data()
        except HTTPException as e:
            print("Supervised session interrupted!")
            raise HTTPException(
                status_code=e.status_code, detail=f"Request failed: {e!s}",
            ) from e

    print("Overload handled!")
