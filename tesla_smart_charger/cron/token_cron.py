"""Python script to run the token refresh cron job."""

import json
import threading
import time
from typing import Any, Dict, Optional

import requests

import tesla_smart_charger.logger as logger
from tesla_smart_charger import constants
from tesla_smart_charger.charger_config import ChargerConfig

# Set up logging
tsc_logger = logger.get_logger()

# Load charger configuration
charger_config = ChargerConfig(constants.CONFIG_FILE)

REFRESH_OK_INTERVAL = 10800   # 3 hours
REFRESH_FAIL_INTERVAL = 300   # 5 minutes


def refresh_tesla_token() -> bool:
    """Refresh the Tesla token."""
    tsc_logger.info("Refreshing Tesla token...")
    load_result = charger_config.load_config()
    if isinstance(load_result, dict) and "error" in load_result:
        tsc_logger.error("Failed to load config: %s", load_result["error"])
        return False
    cfg: Dict[str, Any] = charger_config.get_config() or {}
    client_id: Optional[str] = cfg.get("teslaClientId")
    refresh_token: Optional[str] = cfg.get("teslaRefreshToken")

    if not client_id:
        tsc_logger.error("Tesla client ID not found in configuration.")
        return False
    if not refresh_token:
        tsc_logger.error("Tesla refresh token not found in configuration.")
        return False

    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
        "audience": constants.TESLA_AUDIENCE,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_request = None
    try:
        # Request new token from Tesla API
        token_request = requests.post(
            constants.TESLA_API_TOKEN_URL,
            data=data,
            headers=headers,
            timeout=20,
        )
        token_request.raise_for_status()
        tsc_logger.info("Token request sent successfully.")
    except requests.RequestException as e:
        tsc_logger.error(f"Error refreshing token: {e!s}")
        if token_request is not None:
            tsc_logger.debug(
                "Token request status=%s, body=%r",
                getattr(token_request, "status_code", "?"),
                getattr(token_request, "text", "")[:512],
            )
        return False

    try:
        # Parse the response and update the configuration
        token_response: Dict[str, Any] = token_request.json()

        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = int(token_response.get("expires_in", 0))

        if not access_token or not refresh_token:
            tsc_logger.error("Missing tokens in Tesla response.")
            return False

        cfg["teslaAccessToken"] = access_token
        cfg["teslaRefreshToken"] = refresh_token
        set_result = charger_config.set_config(cfg)
        if isinstance(set_result, dict) and "error" in set_result:
            tsc_logger.error("Failed to persist refreshed tokens: %s", set_result["error"])
            return False
        tsc_logger.info("Tesla token refreshed and updated successfully.")
        if expires_in:
            tsc_logger.info(
                "Token expires at: %s", time.ctime(time.time() + expires_in)
            )
        return True
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        tsc_logger.error(f"Error parsing token response: {e!s}")
        return False
    except Exception as e:
        tsc_logger.error(f"Unexpected error: {e!s}")
        return False


def start_cron_token(stop_event: threading.Event) -> None:
    """Start the cron job to refresh the Tesla token."""
    sleep_time = 2
    refresh_interval = REFRESH_OK_INTERVAL
    tsc_logger.info("Starting cron job for token refresh ...")
    initial_success = refresh_tesla_token()
    refresh_interval = REFRESH_FAIL_INTERVAL if not initial_success else REFRESH_OK_INTERVAL
    time_to_refresh = refresh_interval

    while not stop_event.is_set():
        if time_to_refresh <= 0:
            success = refresh_tesla_token()
            refresh_interval = REFRESH_FAIL_INTERVAL if not success else REFRESH_OK_INTERVAL
            tsc_logger.info(
                "Next token refresh in %ds (%s).",
                refresh_interval,
                "previous failure" if not success else "success",
            )
            time_to_refresh = refresh_interval
        stop_event.wait(sleep_time)
        time_to_refresh -= sleep_time

    tsc_logger.info("Token refresh cron job stopped.")
