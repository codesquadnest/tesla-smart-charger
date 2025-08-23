"""Tesla API class for Tesla Smart Charger."""

import requests
from fastapi import HTTPException
from retrying import retry

from tesla_smart_charger import constants, logger
from tesla_smart_charger.charger_config import ChargerConfig

# Set up logging
tsc_logger = logger.get_logger()


class TeslaAPI:
    """
    Tesla API class for Tesla Smart Charger.

    Attributes
    ----------
    charger_config : ChargerConfig
        The charger configuration.
    """

    def __init__(self, charger_config: ChargerConfig) -> None:
        """
        Initialize the Tesla API.

        Parameters
        ----------
        charger_config : ChargerConfig
            The charger configuration.
        """
        self.charger_config = charger_config
        self.http_proxy = self.charger_config.get_config().get("teslaHttpProxy", None)

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=5000,
        stop_max_attempt_number=5,
    )
    def get_vehicles(self) -> dict:
        """
        Get the vehicles from the Tesla API.

        Returns
        -------
        dict
            The vehicles.
        """
        tsc_logger.info("Requesting vehicles from Tesla API.")

        try:
            vehicle_request = requests.get(
                f"{self.http_proxy}{constants.TESLA_API_VEHICLES_URL}",
                headers={
                    "Authorization": f"Bearer {self.charger_config.get_config().get('teslaAccessToken')}",
                },
                verify=str(constants.TLS_CERT_PATH),
                cert=(str(constants.TLS_CERT_PATH), str(constants.TLS_KEY_PATH)),
                timeout=20,
            )
            vehicle_request.raise_for_status()
        except requests.RequestException as e:
            msg = f"Request 'get_vehicles' failed: {e}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=vehicle_request.status_code, detail=msg)

        response = vehicle_request.json()

        if constants.VERBOSE:
            tsc_logger.debug(response)

        return response.get("response", {})

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=5000,
        stop_max_attempt_number=5,
    )
    def get_vehicle_data(self) -> dict:
        """
        Get the vehicle data from the Tesla API.

        Returns
        -------
        dict
            The vehicle data.
        """
        vehicle_id = self.charger_config.get_config().get("teslaVehicleId")
        tsc_logger.info(f"Requesting data for vehicle ID {vehicle_id} from Tesla API.")

        try:
            vehicle_request = requests.get(
                f"{self.http_proxy}{constants.TESLA_API_VEHICLE_DATA_URL.format(id=vehicle_id)}",
                headers={
                    "Authorization": f"Bearer {self.charger_config.get_config().get('teslaAccessToken')}",
                },
                verify=str(constants.TLS_CERT_PATH),
                cert=(str(constants.TLS_CERT_PATH), str(constants.TLS_KEY_PATH)),
                timeout=20,
            )
            vehicle_request.raise_for_status()
        except requests.RequestException as e:
            msg = f"Request 'get_vehicle_data' failed: {e}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=vehicle_request.status_code, detail=msg)

        response = vehicle_request.json()

        if constants.VERBOSE:
            tsc_logger.debug(response)

        return response.get("response", {})

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=5000,
        stop_max_attempt_number=5,
    )
    def set_charge_amp_limit(self, amp_limit: int) -> dict:
        """
        Set the charge Amperage limit.

        Parameters
        ----------
        amp_limit : int
            The Amperage limit.

        Returns
        -------
        dict
            The response.
        """
        vehicle_id = self.charger_config.get_config().get("teslaVehicleId")
        tsc_logger.info(
            f"Setting charge amperage limit to {amp_limit}A for vehicle ID {vehicle_id}."
        )

        try:
            charge_limit_request = requests.post(
                f"{self.http_proxy}{constants.TESLA_API_CHARGE_AMP_LIMIT_URL.format(id=vehicle_id)}",
                headers={
                    "Authorization": f"Bearer {self.charger_config.get_config().get('teslaAccessToken')}",
                },
                json={"charging_amps": amp_limit},
                verify=str(constants.TLS_CERT_PATH),
                cert=(str(constants.TLS_CERT_PATH), str(constants.TLS_KEY_PATH)),
                timeout=10,
            )
            charge_limit_request.raise_for_status()
        except requests.RequestException as e:
            msg = f"Request 'set_charge_amp_limit' failed: {e}"
            tsc_logger.error(msg)
            raise HTTPException(
                status_code=charge_limit_request.status_code, detail=msg
            )

        response = charge_limit_request.json()

        if constants.VERBOSE:
            tsc_logger.debug(response)

        return response
