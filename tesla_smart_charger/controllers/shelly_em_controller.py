"""
Shelly EM controller implementation

This controller monitors the power consumption of the Shelly EM device
"""

import requests

from retrying import retry

import tesla_smart_charger.constants as constants

from tesla_smart_charger.controllers.em_controller import EnergyMonitorController


class ShellyEMController(EnergyMonitorController):
    def __init__(self: object, host: str) -> None:
        """
        Initializes the Shelly EM controller
        """
        self.type = "shelly_em"
        self.state = constants.EM_CONTROLLER_STATE_IDLE
        self.consumption = 0
        self.last_consumption = 0
        self.emeter0 = 0
        self.emeter1 = 0
        self.url = f"http://{host}/status/"

    def get_state(self: object) -> str:
        """
        Returns the current state of the controller
        """
        return self.state

    def set_state(self: object, state: str) -> None:
        """
        Sets the current state of the controller
        """
        self.state = state

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=10000,
        stop_max_attempt_number=10,
    )
    def get_consumption(self: object) -> float:
        """
        Returns the current consumption of the house
        """
        response = requests.get(self.url)
        response_json = response.json()
        self.last_consumption = self.consumption

        if response.status_code == 200:
            self.emeter0 = response_json["emeters"][0]["power"]
            self.emeter1 = response_json["emeters"][1]["power"]
            self.consumption = self.emeter0 + self.emeter1
        else:
            self.consumption = 0

        return self.consumption
