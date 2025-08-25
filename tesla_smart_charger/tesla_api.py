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
        self.charger_config = charger_config
        cfg = self.charger_config.get_config()
        if "error" in cfg:
            msg = f"Config not loaded: {cfg['error']}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=500, detail=msg)
        self.http_proxy = cfg.get("teslaHttpProxy") or ""

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=5000,
        stop_max_attempt_number=5,
    )
    def get_vehicles(self) -> dict:
        tsc_logger.info("Requesting vehicles from Tesla API.")
        cfg = self.charger_config.get_config()
        if "error" in cfg:
            msg = f"Config not loaded: {cfg['error']}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=500, detail=msg)
        try:
            vehicle_request = requests.get(
                f"{self.http_proxy}{constants.TESLA_API_VEHICLES_URL}",
                headers={
                    "Authorization": f"Bearer {cfg.get('teslaAccessToken')}",
                },
                verify=str(constants.TLS_CERT_PATH),
                cert=(str(constants.TLS_CERT_PATH), str(constants.TLS_KEY_PATH)),
                timeout=20,
            )
            vehicle_request.raise_for_status()
        except requests.RequestException as e:
            status_code = getattr(getattr(e, "response", None), "status_code", 502)
            msg = f"Request 'get_vehicles' failed: {e}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=status_code, detail=msg)
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
        cfg = self.charger_config.get_config()
        if "error" in cfg:
            msg = f"Config not loaded: {cfg['error']}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=500, detail=msg)
        vehicle_id = cfg.get("teslaVehicleId")
        tsc_logger.info(f"Requesting data for vehicle ID {vehicle_id} from Tesla API.")
        try:
            vehicle_request = requests.get(
                f"{self.http_proxy}{constants.TESLA_API_VEHICLE_DATA_URL.format(id=vehicle_id)}",
                headers={
                    "Authorization": f"Bearer {cfg.get('teslaAccessToken')}",
                },
                verify=str(constants.TLS_CERT_PATH),
                cert=(str(constants.TLS_CERT_PATH), str(constants.TLS_KEY_PATH)),
                timeout=20,
            )
            vehicle_request.raise_for_status()
        except requests.RequestException as e:
            status_code = getattr(getattr(e, "response", None), "status_code", 502)
            msg = f"Request 'get_vehicle_data' failed: {e}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=status_code, detail=msg)
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
        cfg = self.charger_config.get_config()
        if "error" in cfg:
            msg = f"Config not loaded: {cfg['error']}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=500, detail=msg)
        vehicle_id = cfg.get("teslaVehicleId")
        tsc_logger.info(
            f"Setting charge amperage limit to {amp_limit}A for vehicle ID {vehicle_id}."
        )
        try:
            charge_limit_request = requests.post(
                f"{self.http_proxy}{constants.TESLA_API_CHARGE_AMP_LIMIT_URL.format(id=vehicle_id)}",
                headers={
                    "Authorization": f"Bearer {cfg.get('teslaAccessToken')}",
                },
                json={"charging_amps": amp_limit},
                verify=str(constants.TLS_CERT_PATH),
                cert=(str(constants.TLS_CERT_PATH), str(constants.TLS_KEY_PATH)),
                timeout=10,
            )
            charge_limit_request.raise_for_status()
        except requests.RequestException as e:
            status_code = getattr(getattr(e, "response", None), "status_code", 502)
            msg = f"Request 'set_charge_amp_limit' failed: {e}"
            tsc_logger.error(msg)
            raise HTTPException(status_code=status_code, detail=msg)
        response = charge_limit_request.json()
        if constants.VERBOSE:
            tsc_logger.debug(response)
        return response
