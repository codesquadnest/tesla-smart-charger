"""Python script to monitor the power consumption of the house."""

import threading
import time
import requests
import schedule
from retrying import retry
from tesla_smart_charger import constants, logger
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.controllers import em_controller as _em_controller

# Set up logging
tsc_logger = logger.get_logger()

OVERLOAD = False

# Load the Tesla charger configuration
tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()

# Initialize energy monitor controller
em_controller = _em_controller.create_energy_monitor_controller(
    tesla_config.config["energyMonitorType"],
    tesla_config.config["energyMonitorIp"],
)


def _reload_config() -> None:
    """Reload the configuration."""
    tesla_config.load_config()
    # tsc_logger.info("Configuration reloaded")


def _toggle_overload(overload: bool) -> bool:
    """Toggle the overload status and return whether it was toggled."""
    global OVERLOAD
    if overload != OVERLOAD:
        OVERLOAD = overload
        tsc_logger.info(f"Overload status changed to: {OVERLOAD}")
        return True
    return False


@retry(
    wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
    wait_exponential_max=10000,
    stop_max_attempt_number=3,
)
def _check_power_consumption() -> None:
    """Check the power consumption of the house."""
    _reload_config()
    try:
        current_em_consumption_amps = em_controller.get_consumption() / 230
        tsc_logger.debug(
            f"Current consumption in amps: {current_em_consumption_amps:.2f}"
        )
    except ValueError as e:
        tsc_logger.error(f"Error getting consumption: {e}")
        return

    if current_em_consumption_amps > float(
        tesla_config.config["homeMaxAmps"]
    ) and _toggle_overload(overload=True):
        tsc_logger.warning("Overload detected!")
        url = (
            f"http://{tesla_config.config.get('hostIp', 'localhost')}:"
            f"{tesla_config.config.get('apiPort', '8000')}/overload"
        )
        try:
            session = requests.Session()
            response = session.get(url, timeout=20)
            if response.status_code not in [200, 202]:
                tsc_logger.error(f"Unexpected status code: {response.status_code}")
                return
        except requests.RequestException as e:
            tsc_logger.error(f"Connection error: {e}")
            return
    else:
        _toggle_overload(overload=False)


def start_cron_monitor(stop_event: threading.Event) -> None:
    """Start the cron job to monitor power consumption."""
    tsc_logger.info("Monitoring started!")
    schedule.every(15).seconds.do(_check_power_consumption)

    while not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)
    
    tsc_logger.info("Monitoring stopped!")
