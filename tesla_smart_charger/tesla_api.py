"""
Tesla API class for Tesla Smart Charger.
"""

import json

import requests

import tesla_smart_charger.constants as constants
from tesla_smart_charger.charger_config import ChargerConfig


class TeslaAPI:
    """Tesla API class for Tesla Smart Charger.

    Attributes:

        charger_config (ChargerConfig): The charger configuration.

    """

    def __init__(self: object, charger_config: ChargerConfig) -> None:
        """Initialize the Tesla API.

        Args:

            charger_config (ChargerConfig): The charger configuration.

        """
        self.charger_config = charger_config

    def get_vehicles(self: object) -> dict:
        """Get the vehicles from the Tesla API.

        Returns:

            dict: The vehicles.

        """
        # Get the vehicles from the Tesla API
        vehicle_request = requests.get(
            constants.TESLA_API_VEHICLES_URL,
            headers={
                "Authorization": f"Bearer {self.charger_config.get_config().get('accessToken', None)}"
            },
        )
        vehicle_response = json.loads(vehicle_request.text)
        print(vehicle_response)

        # Return the vehicles
        return vehicle_response["response"]

    def get_vehicle_data(self: object) -> dict:
        """Get the vehicle data from the Tesla API.

        Returns:

            dict: The vehicle data.

        """
        # Get the vehicle data from the Tesla API
        vehicle_request = requests.get(
            constants.TESLA_API_VEHICLE_DATA_URL.format(
                id=self.charger_config.get_config().get("vehicleId", None)
            ),
            headers={
                "Authorization": f"Bearer {self.charger_config.get_config().get('accessToken', None)}"
            },
        )
        vehicle_response = json.loads(vehicle_request.text)
        print(vehicle_response)

        # Return the vehicle data
        return vehicle_response["response"][0]

    def set_charge_amp_limit(self: object, amp_limit: int) -> dict:
        """Set the charge Amperage limit.

        Args:

            amp_limit (int): The Amperage limit.

        Returns:

            dict: The response.

        """
        # Set the charge Amperage limit
        charge_limit_request = requests.post(
            constants.TESLA_API_CHARGE_AMP_LIMIT_URL.format(
                id=self.charger_config.get_config().get("vehicleId", None)
            ),
            headers={
                "Authorization": f"Bearer {self.charger_config.get_config().get('accessToken', None)}"
            },
            json={"charging_amps": amp_limit},
        )
        charge_limit_response = json.loads(charge_limit_request.text)
        print(charge_limit_response)

        # Return the response
        return charge_limit_response
