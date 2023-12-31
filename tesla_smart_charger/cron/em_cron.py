"""Python script to monitor the power consumption of the house."""

import threading
import time

import requests
import schedule
from retrying import retry

from tesla_smart_charger import constants
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.controllers import em_controller as _em_controller

OVERLOAD = False

tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()

em_controller = _em_controller.create_energy_monitor_controller(
    tesla_config.config["energyMonitorType"],
    tesla_config.config["energyMonitorIp"],
)


def _reload_config() -> None:
    """Reload the config."""
    tesla_config.load_config()


def _toggle_overload(overload: True) -> bool:
    """Toggle the overload."""
    global OVERLOAD
    if overload != OVERLOAD and overload is True:
        OVERLOAD = True
        return True
    if overload != OVERLOAD and overload is False:
        OVERLOAD = False
    return False


@retry(
    wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
    wait_exponential_max=10000,
    stop_max_attempt_number=5,
)
def _check_power_consumption() -> None:
    """Check the power consumption of the house."""
    # Get the current charge limit
    _reload_config()
    try:
        current_em_consumption_amps = em_controller.get_consumption() / 230
    except ValueError as e:
        print(f"Error getting consumption: {e!s}")
        return

    if current_em_consumption_amps > tesla_config.config[
        "homeMaxAmps"
    ] and _toggle_overload(overload=True):
        print("Overload detected!")
        # Call the overload handler endpoint using requests
        try:
            requests.get(
                (
                    f"http://127.0.0.1:{tesla_config.config.get('apiPort', '8000')}"
                    "/overload"
                ),
                timeout=20,
            )
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {e!s}")
            return
    else:
        _toggle_overload(overload=False)


def start_cron_monitor(stop_event: threading.Event) -> None:
    """Start the cron job to monitor power consumption."""
    print("Monitoring started!")
    schedule.every(10).seconds.do(_check_power_consumption)

    while not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)
