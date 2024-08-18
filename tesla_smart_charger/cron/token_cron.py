"""Python script to run the token refresh cron job."""

import json
import threading
import time

import requests
import schedule

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

    data = {
        "grant_type": "refresh_token",
        "client_id": charger_config.get_config().get("teslaClientId", None),
        "refresh_token": charger_config.get_config().get("teslaRefreshToken", None),
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
        return

    try:
        # Parse the response and update the configuration
        token_response = token_request.json()
        charger_config.config["teslaAccessToken"] = token_response["access_token"]
        charger_config.config["teslaRefreshToken"] = token_response["refresh_token"]
        charger_config.set_config(json.dumps(charger_config.config))
        tsc_logger.info("Tesla token refreshed and updated successfully.")
    except (KeyError, json.JSONDecodeError) as e:
        tsc_logger.error(f"Error parsing token response: {e!s}")


def start_cron_token(stop_event: threading.Event) -> None:
    """Start the cron job to refresh the Tesla token."""
    tsc_logger.info("Starting cron job for token refresh ...")
    refresh_tesla_token()
    schedule.every(2).hours.do(refresh_tesla_token)

    while not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)
    
    tsc_logger.info("Token refresh cron job stopped.")
