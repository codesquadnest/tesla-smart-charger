"""
Tesla API class for Tesla Smart Charger.
"""

import json

import requests
from retrying import retry

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

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
    def get_vehicles(self: object) -> dict:
        """Get the vehicles from the Tesla API.

        Returns:

            dict: The vehicles.

        """
        # Get the vehicles from the Tesla API
        vehicle_request = requests.get(
            constants.TESLA_API_VEHICLES_URL,
            headers={
                "Authorization": f"Bearer {self.charger_config.get_config().get('teslaAccessToken', None)}"
            },
        )

        if vehicle_request.status_code != 200:
            raise Exception("Request 'get_vehicles' failed with status code {}".format(vehicle_request.status_code))

        response = json.loads(vehicle_request.text)
        
        if constants.VERBOSE:
            print(response)

        return response["response"]


    @retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
    def get_vehicle_data(self: object) -> dict:
        """Get the vehicle data from the Tesla API.

        Returns:

            dict: The vehicle data.

        """
        # Get the vehicle data from the Tesla API
        vehicle_request = requests.get(
            constants.TESLA_API_VEHICLE_DATA_URL.format(
                id=self.charger_config.get_config().get("teslaVehicleId", None)
            ),
            headers={
                "Authorization": f"Bearer {self.charger_config.get_config().get('teslaAccessToken', None)}"
            },
        )
        if vehicle_request.status_code != 200:
            raise Exception("Request 'get_vehicle_data' failed with status code {}".format(vehicle_request.status_code))

        response = json.loads(vehicle_request.text)

        if constants.VERBOSE:
            print(response)

        return response["response"]

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
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
                id=self.charger_config.get_config().get("teslaVehicleId", None)
            ),
            headers={
                "Authorization": f"Bearer {self.charger_config.get_config().get('teslaAccessToken', None)}"
            },
            json={"charging_amps": amp_limit},
        )
        if charge_limit_request.status_code != 200:
            raise Exception("Request 'set_charge_amp_limit' failed with status code {}".format(charge_limit_request.status_code))

        response = json.loads(charge_limit_request.text)

        if constants.VERBOSE:
            print(response)
        
        return response
