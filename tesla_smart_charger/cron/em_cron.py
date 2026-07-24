"""Energy-monitor polling cron — triggers overload handling when needed."""

import threading

from retrying import retry

from tesla_smart_charger import constants, logger
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.controllers import em_controller as _em_controller
from tesla_smart_charger.controllers.em_controller import EnergyMonitorController
from tesla_smart_charger.handlers import overload_handler

tsc_logger = logger.get_logger()

# Global overload flag (toggled by this module only)
OVERLOAD = False

# Latest consumption reading in amps — written by the cron on each poll,
# read by the status endpoint so the dashboard shows live home consumption.
# Initialised to None so the dashboard shows "—" until the first poll.
LAST_CONSUMPTION_AMPS: float | None = None


def _toggle_overload(*, overload: bool) -> bool:
    """Set the OVERLOAD flag; returns True if the value changed."""
    global OVERLOAD
    if overload != OVERLOAD:
        OVERLOAD = overload
        tsc_logger.info("Overload flag → %s", OVERLOAD)
        return True
    return False


def _get_em_controller(app_config: AppConfig) -> EnergyMonitorController | None:
    """Create and return an energy monitor controller, or None on failure."""
    cfg = app_config.system
    if not cfg.energyMonitorType or not cfg.energyMonitorIp:
        tsc_logger.error(
            "Energy monitor not configured (type=%r, ip=%r).",
            cfg.energyMonitorType,
            cfg.energyMonitorIp,
        )
        return None
    try:
        return _em_controller.create_energy_monitor_controller(
            cfg.energyMonitorType, cfg.energyMonitorIp
        )
    except ValueError:
        tsc_logger.exception("Invalid EM controller type")
        return None


@retry(
    wait_exponential_multiplier=constants.REQUEST_DELAY_MS,
    wait_exponential_max=10000,
    stop_max_attempt_number=3,
)
def _check_power_consumption(
    em_ctrl: EnergyMonitorController, app_config: AppConfig
) -> None:
    """Poll the energy monitor and trigger overload handling if needed."""
    cfg = app_config.system

    try:
        watts = em_ctrl.get_consumption()
        if watts is None:
            # Unify with the RequestException path below via one except block.
            msg = "EM returned None"
            raise ValueError(msg)  # noqa: TRY301
        em_amps = float(watts) / max(cfg.voltage, 1.0)
        tsc_logger.debug("Consumption: %.2f A (%.1f W)", em_amps, watts)
        global LAST_CONSUMPTION_AMPS
        LAST_CONSUMPTION_AMPS = em_amps
    except (ValueError, TypeError):
        tsc_logger.exception("Error reading consumption")
        return

    if em_amps > cfg.homeMaxAmps and _toggle_overload(overload=True):
        tsc_logger.warning(
            "Overload detected! %.2f A > %.2f A", em_amps, cfg.homeMaxAmps
        )
        # Trigger directly — no HTTP round-trip needed
        started, msg = overload_handler.trigger_overload(app_config)
        if not started:
            tsc_logger.info("Overload trigger skipped: %s", msg)
            _toggle_overload(overload=False)  # Reset so next poll can retry
    else:
        _toggle_overload(overload=False)


def start_cron_monitor(stop_event: threading.Event, app_config: AppConfig) -> None:
    """Cron thread: polls the energy monitor every 15 seconds."""
    tsc_logger.info("Energy monitor cron started.")

    em_ctrl = _get_em_controller(app_config)
    if em_ctrl is None:
        tsc_logger.error("Could not initialise EM controller — monitor cron exiting.")
        return

    sleep_tick = 1
    check_interval = 15
    countdown = check_interval

    while not stop_event.is_set():
        if countdown <= 0:
            try:
                _check_power_consumption(em_ctrl, app_config)
            # Deliberately broad: this is the cron loop's top-level guard —
            # any unexpected error here must be logged, not crash the thread.
            except Exception:
                tsc_logger.exception("Unhandled error in energy monitor poll")
            countdown = check_interval
        stop_event.wait(sleep_tick)
        countdown -= sleep_tick

    tsc_logger.info("Energy monitor cron stopped.")
