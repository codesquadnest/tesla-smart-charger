"""
Python script to run the token refresh cron job.
"""

import json
import requests
import schedule
import threading
import time

import tesla_smart_charger.constants as constants
from tesla_smart_charger.charger_config import ChargerConfig

charger_config = ChargerConfig(constants.CONFIG_FILE)


def refresh_tesla_token():
    print("Refreshing token!")
    charger_config.load_config()

    refresh_json = {
        "grant_type": "refresh_token",
        "client_id": "ownerapi",
        "refresh_token": charger_config.get_config().get("refreshToken", None),
        "scope": "openid email offline_access vehicle_cmds vehicle_charging_cmds",
    }
    print(refresh_json)

    # Request new token from Tesla API
    token_request = requests.post(constants.TESLA_API_TOKEN_URL, json=refresh_json)
    print("New Token : " + token_request.text)

    # Parse the response
    token_response = json.loads(token_request.text)
    print(token_response)

    # Update the config file
    charger_config.config["accessToken"] = token_response["access_token"]
    charger_config.config["refreshToken"] = token_response["refresh_token"]
    charger_config.set_config(json.dumps(charger_config.config))


def start_cron_job(stop_event: threading.Event):
    # Run the job every minute
    schedule.every(6).hours.do(refresh_tesla_token)

    while not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_cron_job()
