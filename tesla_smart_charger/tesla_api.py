"""Tesla Fleet API client — per-vehicle instance."""

import requests
from fastapi import HTTPException
from retrying import retry

from tesla_smart_charger import constants, logger
from tesla_smart_charger.models import VehicleConfig

tsc_logger = logger.get_logger()


class TeslaAPI:
    """
    Tesla Fleet API client for a single vehicle.

    All vehicle commands are routed through the local ``tesla-http-proxy``
    container which handles mutual TLS and request signing.

    Parameters
    ----------
    vehicle:
        The vehicle configuration containing credentials and proxy settings.
    """

    def __init__(self, vehicle: VehicleConfig) -> None:
        self.vehicle = vehicle

    # ─── Internal helpers ──────────────────────────────────────────────────────

    @property
    def _proxy(self) -> str:
        return self.vehicle.teslaHttpProxy

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.vehicle.teslaAccessToken}"}

    def _tls(self) -> dict:
        return {
            "verify": str(constants.TLS_CERT_PATH),
            "cert": (str(constants.TLS_CERT_PATH), str(constants.TLS_KEY_PATH)),
        }

    def _raise(self, exc: requests.RequestException, label: str) -> None:
        status = getattr(getattr(exc, "response", None), "status_code", 502)
        msg = f"{label} failed for vehicle {self.vehicle.teslaVehicleId}: {exc}"
        tsc_logger.error(msg)
        raise HTTPException(status_code=status, detail=msg) from exc

    # ─── API methods ───────────────────────────────────────────────────────────

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=5000,
        stop_max_attempt_number=5,
    )
    def get_vehicles(self) -> list:
        """Return the list of Tesla vehicles linked to this OAuth token."""
        tsc_logger.info("Requesting vehicle list from Tesla API.")
        try:
            r = requests.get(
                f"{self._proxy}{constants.TESLA_API_VEHICLES_URL}",
                headers=self._headers(),
                **self._tls(),
                timeout=20,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            self._raise(exc, "get_vehicles")
        response = r.json()
        if constants.VERBOSE:
            tsc_logger.debug(response)
        return response.get("response", [])

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=5000,
        stop_max_attempt_number=5,
    )
    def get_vehicle_data(self) -> dict:
        """Return full telemetry for this vehicle."""
        vehicle_id = self.vehicle.teslaVehicleId
        if not vehicle_id:
            raise HTTPException(
                status_code=400, detail="teslaVehicleId is not set on this vehicle config"
            )
        tsc_logger.info(f"Requesting data for vehicle {vehicle_id}.")
        try:
            r = requests.get(
                f"{self._proxy}{constants.TESLA_API_VEHICLE_DATA_URL.format(id=vehicle_id)}",
                headers=self._headers(),
                **self._tls(),
                timeout=20,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            self._raise(exc, "get_vehicle_data")
        response = r.json()
        if constants.VERBOSE:
            tsc_logger.debug(response)
        return response.get("response", {})

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=5000,
        stop_max_attempt_number=5,
    )
    def set_charge_amp_limit(self, amp_limit: int) -> dict:
        """Command this vehicle to set its charging amp limit."""
        vehicle_id = self.vehicle.teslaVehicleId
        tsc_logger.info(f"Setting charge limit → {amp_limit}A for vehicle {vehicle_id}.")
        try:
            r = requests.post(
                f"{self._proxy}{constants.TESLA_API_CHARGE_AMP_LIMIT_URL.format(id=vehicle_id)}",
                headers=self._headers(),
                json={"charging_amps": amp_limit},
                **self._tls(),
                timeout=10,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            self._raise(exc, "set_charge_amp_limit")
        response = r.json()
        if constants.VERBOSE:
            tsc_logger.debug(response)
        return response

    def refresh_token(self, region: str = "eu") -> tuple[str, str] | None:
        """
        Exchange the vehicle's refresh_token for a new access/refresh token pair.

        Returns ``(access_token, refresh_token)`` on success, ``None`` on failure.
        """
        audience = constants.TESLA_FLEET_API_URLS.get(region, constants.TESLA_AUDIENCE)
        data = {
            "grant_type": "refresh_token",
            "client_id": self.vehicle.teslaClientId,
            "refresh_token": self.vehicle.teslaRefreshToken,
            "audience": audience,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            r = requests.post(
                constants.TESLA_API_TOKEN_URL,
                data=data,
                headers=headers,
                timeout=20,
            )
            r.raise_for_status()
            body = r.json()
            access = body.get("access_token")
            refresh = body.get("refresh_token")
            if not access or not refresh:
                tsc_logger.error("Missing tokens in Tesla refresh response.")
                return None
            # Keep local copy in sync
            self.vehicle = self.vehicle.model_copy(
                update={"teslaAccessToken": access, "teslaRefreshToken": refresh}
            )
            return access, refresh
        except requests.RequestException as exc:
            tsc_logger.error(f"Token refresh failed for vehicle {self.vehicle.id}: {exc}")
            return None
