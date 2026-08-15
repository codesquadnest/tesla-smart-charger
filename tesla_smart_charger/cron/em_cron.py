"""Energy-monitor polling cron — triggers overload handling when needed."""

import threading
import time

from retrying import retry

from tesla_smart_charger import constants, logger
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.controllers import em_controller as _em_controller
from tesla_smart_charger.controllers.em_controller import EnergyMonitorController
from tesla_smart_charger.handlers import overload_handler, solar_handler

tsc_logger = logger.get_logger()

# Global overload flag (toggled by this module only)
OVERLOAD = False

# Latest consumption reading in amps — written by the cron on each poll,
# read by the status endpoint so the dashboard shows live home consumption.
# Initialised to None so the dashboard shows "—" until the first poll.
LAST_CONSUMPTION_AMPS: float | None = None

# Latest export in amps (0 when consuming) — for the solar surplus indicator.
LAST_SURPLUS_AMPS: float | None = None

# Cooldown between solar trigger attempts — the solar handler runs its own
# supervised thread, so the cron only needs to kick it off once surplus is
# detected, not on every poll.
_SOLAR_TRIGGER_COOLDOWN_SECS = 30
_last_solar_attempt: float = 0.0


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
        global LAST_CONSUMPTION_AMPS, LAST_SURPLUS_AMPS
        LAST_CONSUMPTION_AMPS = em_amps
        LAST_SURPLUS_AMPS = max(0.0, -em_amps)
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
        if LAST_SURPLUS_AMPS is not None and LAST_SURPLUS_AMPS > 0.5:
            _start_solar_if_needed(app_config)


def _start_solar_if_needed(app_config: AppConfig) -> None:
    """Start a solar surplus session when surplus is exporting and solar mode is on."""
    cfg = app_config.system
    global _last_solar_attempt
    if not cfg.solarSurplusEnabled:
        return
    if time.monotonic() - _last_solar_attempt < _SOLAR_TRIGGER_COOLDOWN_SECS:
        return
    _last_solar_attempt = time.monotonic()
    started, msg = solar_handler.trigger_solar(app_config)
    if started:
        tsc_logger.info("Solar surplus session triggered.")
    elif solar_handler.is_surplus_active():
        pass  # already running — no noise
    else:
        tsc_logger.debug("Solar trigger skipped: %s", msg)


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
