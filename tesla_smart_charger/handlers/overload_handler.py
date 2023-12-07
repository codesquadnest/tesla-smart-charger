"""
Handles the overload of the charger
"""

import time

import tesla_smart_charger.constants as constants
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.tesla_api import TeslaAPI

tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_api = TeslaAPI(tesla_config)


def handle_overload():
    """
    Handles the overload of the charger
    """
    tesla_config.load_config()
    # Sleep duration in seconds according to the config file
    # time.sleep(int(tesla_config.config["sleepTime"]))
    time.sleep(10)

    # Get the current vehicle data
    # vehicle_data = tesla_api.get_vehicle_data()

    # TODO: Handle the overload of the charger
    # print(vehicle_data)
    print("Overload handled!")

