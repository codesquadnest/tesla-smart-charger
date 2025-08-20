"""Python script to monitor the power consumption of the house."""

import threading
import requests
from retrying import retry
from typing import Optional

from tesla_smart_charger import constants, logger
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.controllers import em_controller as _em_controller

# Set up logging
tsc_logger = logger.get_logger()

OVERLOAD = False

# Load the Tesla charger configuration
tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()

# Initialize energy monitor controller safely
em_controller = None
try:
    em_type = tesla_config.config.get("energyMonitorType")
    em_ip = tesla_config.config.get("energyMonitorIp")
    if em_type and em_ip:
        em_controller = _em_controller.create_energy_monitor_controller(em_type, em_ip)
    else:
        tsc_logger.error("Energy monitor configuration missing (type or IP).")
except Exception as e:
    tsc_logger.error(f"Error creating energy monitor controller: {e!s}")


def _reload_config() -> None:
    """Reload the configuration safely."""
    try:
        tesla_config.load_config()
    except Exception as e:
        tsc_logger.error(f"Failed to reload config: {e!s}")


def _toggle_overload(overload: bool) -> bool:
    """Toggle the overload status and return whether it was toggled."""
    global OVERLOAD
    if overload != OVERLOAD:
        OVERLOAD = overload
        tsc_logger.info("Overload status changed to: %s", OVERLOAD)
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

    if em_controller is None:
        tsc_logger.error("Energy monitor controller not initialized.")
        return

    try:
        consumption = em_controller.get_consumption()
        if consumption is None:
            raise ValueError("Energy monitor returned None")
        current_em_consumption_amps = float(consumption) / 230.0
        tsc_logger.debug(
            "Current consumption in amps: %.2f", current_em_consumption_amps
        )
    except (ValueError, TypeError) as e:
        tsc_logger.error(f"Error getting consumption: {e!s}")
        return

    try:
        max_amps_str: Optional[str] = tesla_config.config.get("homeMaxAmps")
        max_amps = float(max_amps_str) if max_amps_str is not None else 0.0
    except ValueError:
        tsc_logger.error(
            f"Invalid homeMaxAmps value: {tesla_config.config.get('homeMaxAmps')}"
        )
        return

    if current_em_consumption_amps > max_amps and _toggle_overload(overload=True):
        tsc_logger.warning("Overload detected!")
        host_ip = tesla_config.config.get("hostIp", "localhost")
        api_port = tesla_config.config.get("apiPort", "8000")
        url = f"http://{host_ip}:{api_port}/overload"

        try:
            with requests.Session() as session:
                response = session.get(url, timeout=20)
                if response.status_code not in (200, 202):
                    tsc_logger.error(
                        "Unexpected status code %s from overload endpoint, body=%r",
                        response.status_code,
                        response.text,
                    )
        except requests.RequestException as e:
            tsc_logger.error(f"Connection error: {e!s}")
    else:
        _toggle_overload(overload=False)


def start_cron_monitor(stop_event: threading.Event) -> None:
    """Start the cron job to monitor power consumption."""
    tsc_logger.info("Monitoring started!")
    sleep_time = 1
    check_interval = 15
    time_to_check_power_consumption = check_interval

    while not stop_event.is_set():
        if time_to_check_power_consumption <= 0:
            _check_power_consumption()
            time_to_check_power_consumption = check_interval
        # wait is better than sleep → responds to stop_event quickly
        stop_event.wait(sleep_time)
        time_to_check_power_consumption -= sleep_time

    tsc_logger.info("Monitoring stopped!")
