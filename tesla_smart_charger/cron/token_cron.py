"""Python script to run the token refresh cron job."""

import json
import threading
import time

import requests

import tesla_smart_charger.logger as logger
from tesla_smart_charger import constants
from tesla_smart_charger.charger_config import ChargerConfig

# Set up logging
tsc_logger = logger.get_logger()

# Load charger configuration
charger_config = ChargerConfig(constants.CONFIG_FILE)


def refresh_tesla_token() -> None:
    """Refresh the Tesla token."""
    tsc_logger.info("Refreshing Tesla token...")
    charger_config.load_config()

    client_id = charger_config.get_config().get("teslaClientId", None)
    if not client_id:
        tsc_logger.error("Tesla client ID not found in configuration.")
        return
    refresh_token = charger_config.get_config().get("teslaRefreshToken", None)
    if not refresh_token:
        tsc_logger.error("Tesla refresh token not found in configuration.")
        return

    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
        "audience": constants.TESLA_AUDIENCE,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        # Request new token from Tesla API
        token_request = requests.post(
            constants.TESLA_API_TOKEN_URL,
            data=data,
            headers=headers,
            timeout=20,
        )
        token_request.raise_for_status()  # Raises an error for HTTP codes 4xx/5xx
        tsc_logger.info("Token request sent successfully.")
    except requests.RequestException as e:
        tsc_logger.error(f"Error refreshing token: {e!s}")
        # Debug token request
        tsc_logger.debug(f"Token request: {token_request!r}")
        return

    try:
        # Parse the response and update the configuration
        token_response = token_request.json()
        charger_config.config["teslaAccessToken"] = token_response["access_token"]
        charger_config.config["teslaRefreshToken"] = token_response["refresh_token"]
        expires_in = token_response["expires_in"]
        charger_config.set_config(json.dumps(charger_config.config))
        tsc_logger.info("Tesla token refreshed and updated successfully.")
        tsc_logger.info(f"Token expires at: {time.ctime(time.time() + expires_in)}")
    except (KeyError, json.JSONDecodeError) as e:
        tsc_logger.error(f"Error parsing token response: {e!s}")


def start_cron_token(stop_event: threading.Event) -> None:
    """Start the cron job to refresh the Tesla token."""
    sleep_time = 2
    time_to_refresh = 10800

    tsc_logger.info("Starting cron job for token refresh ...")
    refresh_tesla_token()
    time.sleep(sleep_time)

    while not stop_event.is_set():
        time_to_refresh -= sleep_time
        if time_to_refresh <= 0:
            refresh_tesla_token()
            time_to_refresh = 10800
        time.sleep(sleep_time)

    tsc_logger.info("Token refresh cron job stopped.")
