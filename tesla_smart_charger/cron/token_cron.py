"""Python script to run the token refresh cron job."""

import json
import threading
import time

import requests
import schedule

from tesla_smart_charger import constants
from tesla_smart_charger.charger_config import ChargerConfig

charger_config = ChargerConfig(constants.CONFIG_FILE)


def refresh_tesla_token() -> None:
    """Refresh the Tesla token."""
    print("Refreshing token!")
    charger_config.load_config()

    refresh_json = {
        "grant_type": "refresh_token",
        "client_id": "ownerapi",
        "refresh_token": charger_config.get_config().get("teslaRefreshToken", None),
        "scope": "openid email offline_access vehicle_cmds vehicle_charging_cmds",
    }
    print(refresh_json)

    # Request new token from Tesla API
    token_request = requests.post(
        constants.TESLA_API_TOKEN_URL, json=refresh_json, timeout=20,
    )
    print(f"New Token : {token_request.text}")

    # Parse the response
    token_response = json.loads(token_request.text)
    print(token_response)

    # Update the config file
    charger_config.config["teslaAccessToken"] = token_response["access_token"]
    charger_config.config["teslaRefreshToken"] = token_response["refresh_token"]
    charger_config.set_config(json.dumps(charger_config.config))


def start_cron_token(stop_event: threading.Event) -> None:
    """Start the cron job to refresh the Tesla token."""
    schedule.every(6).hours.do(refresh_tesla_token)

    while not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)
