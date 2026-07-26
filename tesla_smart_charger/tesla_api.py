"""Tesla Fleet API client — per-vehicle instance."""

import os
import warnings

import requests
from fastapi import HTTPException
from retrying import retry
from urllib3.exceptions import InsecureRequestWarning

from tesla_smart_charger import constants, logger
from tesla_smart_charger.models import VehicleConfig

# Suppress "Unverified HTTPS request" warning — the proxy's self-signed cert
# is expected on the private Docker network; mTLS client auth still applies.
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

tsc_logger = logger.get_logger()


class TeslaAPI:
    """
    Tesla Fleet API client for a single vehicle.

    All vehicle commands are routed through the local ``tesla-http-proxy``
    container which handles mutual TLS and request signing.

    When the proxy URL is set to a direct Fleet API URL (e.g.
    ``https://fleet-api.prd.eu.vn.cloud.tesla.com``), TLS certificates
    are skipped — the request goes directly to the Fleet API with only
    a Bearer token.

    Parameters
    ----------
    vehicle:
        The vehicle configuration containing credentials and proxy settings.

    """

    def __init__(self, vehicle: VehicleConfig) -> None:
        """Build a client bound to a single vehicle's config and credentials."""
        self.vehicle = vehicle

    # ─── Internal helpers ──────────────────────────────────────────────────────

    @property
    def _proxy(self) -> str:
        return os.environ.get("TESLA_PROXY_URL", self.vehicle.teslaHttpProxy)

    @property
    def _fleet_api_url(self) -> str:
        """
        The Fleet API base URL for this vehicle's region.

        Uses the proxy URL directly if it's already a Fleet API URL
        (set by users who don't run the tesla-http-proxy), otherwise
        derives it from the region.
        """
        proxy = self._proxy
        if any(
            proxy.startswith(url) for url in constants.TESLA_FLEET_API_URLS.values()
        ):
            return proxy
        return constants.TESLA_FLEET_API_URLS.get(
            self.vehicle.region, constants.TESLA_AUDIENCE
        )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.vehicle.teslaAccessToken}"}

    def _tls(self) -> dict:
        """
        MTLS certs — only sent when the proxy is NOT a direct Fleet API URL.

        Server certificate verification is disabled because the proxy's self-
        signed cert CN won't match the Docker service name (tesla-http-proxy).
        """
        proxy = self._proxy
        if any(
            proxy.startswith(url) for url in constants.TESLA_FLEET_API_URLS.values()
        ):
            return {}
        return {
            "verify": False,
            "cert": (str(constants.TLS_CERT_PATH), str(constants.TLS_KEY_PATH)),
        }

    def _raise(self, exc: requests.RequestException, label: str) -> None:
        status = getattr(getattr(exc, "response", None), "status_code", 502)
        msg = f"{label} failed for vehicle {self.vehicle.teslaVehicleId}: {exc}"
        if status == 408:
            tsc_logger.debug(msg)
        else:
            tsc_logger.error(msg)
        raise HTTPException(status_code=status, detail=msg) from exc

    # ─── API methods ───────────────────────────────────────────────────────────

    @retry(
        wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
        wait_exponential_max=5000,
        stop_max_attempt_number=5,
    )
    def get_vehicles(self) -> list:
        """
        Return the list of Tesla vehicles linked to this OAuth token.

        Uses the Fleet API directly (Bearer token only, no mTLS), even
        when a tesla-http-proxy is configured — listing vehicles does
        not require mutual TLS.
        """
        tsc_logger.info("Requesting vehicle list from Tesla API.")
        try:
            r = requests.get(
                f"{self._fleet_api_url}{constants.TESLA_API_VEHICLES_URL}",
                headers=self._headers(),
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
                status_code=400,
                detail="teslaVehicleId is not set on this vehicle config",
            )
        tsc_logger.info("Requesting data for vehicle %s.", vehicle_id)
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
        # Use the VIN (17 chars) for command URLs — the tesla-http-proxy rejects
        # numeric Fleet API IDs in command paths.
        vehicle_id = self.vehicle.vin or self.vehicle.teslaVehicleId
        tsc_logger.info(
            "Setting charge limit → %sA for vehicle %s.", amp_limit, vehicle_id
        )
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

    def _send_command(self, command: str, payload: dict) -> dict:
        """
        Send a signed vehicle command through the proxy.

        Not retried: `retrying` retries on any exception, so a 4xx (expired
        token, car asleep) would burn five attempts before the caller hears
        about it — unhelpful for an interactive command.
        """
        # Use the VIN (17 chars) for command URLs — the tesla-http-proxy rejects
        # numeric Fleet API IDs in command paths.
        vehicle_id = self.vehicle.vin or self.vehicle.teslaVehicleId
        if not vehicle_id:
            raise HTTPException(
                status_code=400,
                detail="Neither vin nor teslaVehicleId is set on this vehicle config",
            )
        tsc_logger.info("Sending command %s to vehicle %s.", command, vehicle_id)
        url = constants.TESLA_API_COMMAND_URL.format(id=vehicle_id, command=command)
        try:
            r = requests.post(
                f"{self._proxy}{url}",
                headers=self._headers(),
                json=payload,
                **self._tls(),
                timeout=10,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            self._raise(exc, command)
        response = r.json()
        if constants.VERBOSE:
            tsc_logger.debug(response)
        self._raise_on_rejection(response, command)
        return response

    def _raise_on_rejection(self, response: dict, command: str) -> None:
        """
        Turn a vehicle-level command rejection into an error.

        Tesla answers a refused command with HTTP 200 and
        ``{"response": {"result": false, "reason": "..."}}`` — typically when
        the car is asleep or unreachable.  Without this check the caller would
        report success and the dashboard would show a change that never
        happened.
        """
        result = response.get("response")
        if not isinstance(result, dict) or result.get("result") is not False:
            return
        reason = result.get("reason") or "no reason given"
        msg = f"Vehicle rejected {command}: {reason}"
        tsc_logger.error(msg)
        # 409: the request was well-formed, but the car's current state (asleep,
        # unreachable) prevents it — a retry after waking may well succeed.
        raise HTTPException(status_code=409, detail=msg)

    def set_charge_limit(self, percent: int) -> dict:
        """Command this vehicle to set its target state of charge."""
        return self._send_command("set_charge_limit", {"percent": percent})

    def wake_up(self) -> dict:
        """
        Ask Tesla to wake this vehicle.

        Goes directly to the Fleet API (Bearer token only, no mTLS) because
        waking requires no command signing — so it still works when the
        tesla-http-proxy is down.  Uses the numeric vehicle id, not the VIN:
        the VIN preference elsewhere exists only because the proxy rejects
        numeric ids on command paths.

        Waking is asynchronous — a successful response means Tesla accepted
        the request, not that the car is awake yet.
        """
        vehicle_id = self.vehicle.teslaVehicleId
        if not vehicle_id:
            raise HTTPException(
                status_code=400,
                detail="teslaVehicleId is not set on this vehicle config",
            )
        tsc_logger.info("Waking vehicle %s.", vehicle_id)
        url = constants.TESLA_API_WAKE_UP_URL.format(id=vehicle_id)
        try:
            r = requests.post(
                f"{self._fleet_api_url}{url}",
                headers=self._headers(),
                timeout=15,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            self._raise(exc, "wake_up")
        response = r.json()
        if constants.VERBOSE:
            tsc_logger.debug(response)
        return response.get("response", {})

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
        except requests.RequestException:
            tsc_logger.exception("Token refresh failed for vehicle %s", self.vehicle.id)
            return None
        else:
            return access, refresh
