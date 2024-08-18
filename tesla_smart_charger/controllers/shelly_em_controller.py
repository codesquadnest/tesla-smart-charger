"""
Shelly EM Controller Implementation.

This controller monitors and manages the power consumption of the Shelly EM device.
"""

import requests
from retrying import retry

from tesla_smart_charger import constants
from tesla_smart_charger.controllers.em_controller import EnergyMonitorController


class ShellyEMController(EnergyMonitorController):
    """Implementation of the Shelly EM energy monitor controller."""

    def __init__(self, host: str) -> None:
        """
        Initialize the Shelly EM controller.

        Args:
            host (str): The IP address or hostname of the Shelly EM device.
        """
        self.type = "shelly_em"
        self.state = constants.EM_CONTROLLER_STATE_IDLE
        self.consumption = 0.0
        self.last_consumption = 0.0
        self.emeter0 = 0.0
        self.emeter1 = 0.0
        self.url = f"http://{host}/status/"

    def get_state(self) -> str:
        """
        Get the current state of the controller.

        Returns:
            str: The current state of the controller.
        """
        return self.state

    def set_state(self, state: str) -> None:
        """
        Set the current state of the controller.

        Args:
            state (str): The new state of the controller.
        """
        self.state = state

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=10000,
        stop_max_attempt_number=1,
    )
    def get_consumption(self) -> float:
        """
        Get the current power consumption of the house.

        Returns:
            float: The current power consumption in watts.

        Raises:
            ValueError: If there is an error retrieving the consumption data.
        """
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            data = response.json()
        except requests.RequestException as e:
            raise ValueError(f"Error getting consumption: {e}") from e

        # Save the last known consumption
        self.last_consumption = self.consumption

        # Extract and sum the power readings from both meters
        self.emeter0 = data.get("emeters", [{}])[0].get("power", 0.0)
        self.emeter1 = data.get("emeters", [{}])[1].get("power", 0.0)
        self.consumption = self.emeter0 + self.emeter1

        return self.consumption
