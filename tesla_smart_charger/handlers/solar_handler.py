"""
Solar surplus charging handler.

When ``solarSurplusEnabled`` is on and the grid feed reading is net *export*,
the solar handler sizes each charging vehicle's current so the export is
absorbed instead of sold back to the grid, keeping net grid import as close to
``solarTargetAmps`` as possible.  If there is no surplus, vehicles are throttled
back toward their configured minimum so the app does not buy grid power purely
for charging.  Grid protection still applies: any consumption above
``homeMaxAmps`` defers to the overload handler.

Runs as its own supervised session thread, mirroring ``overload_handler``.
"""

import math
import threading
import time

from fastapi import HTTPException

from tesla_smart_charger import logger
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.controllers import em_controller as _em_controller
from tesla_smart_charger.controllers.em_controller import EnergyMonitorController
from tesla_smart_charger.handlers import overload_handler
from tesla_smart_charger.models import SystemConfig, VehicleConfig
from tesla_smart_charger.tesla_api import TeslaAPI

tsc_logger = logger.get_logger()

# Lock that guards the solar session flag
_session_lock = threading.Lock()
_session_active = False

# Hard safety bound for a single supervised solar session.  Solar sessions are
# meant to ride an afternoon of sun, so unlike the overload handler they do not
# end via the user's maxSessionDuration (which would churn restarts all day) —
# they end when the grid is balanced or there is nothing left to adjust.
_SOLAR_MAX_SECONDS = 6 * 3600

# Consecutive no-change readings needed before ending a solar session.
_STABLE_NEEDED = 3

# Minimum grid drift (amps) that warrants adjusting a vehicle's charge current.
# Anything smaller would turn a 0.2A measurement wobble into a full 1A command
# and flap between two amps every poll.
_DEADBAND_AMPS = 1.0


def is_surplus_active() -> bool:
    """Return whether a solar surplus session is currently active."""
    with _session_lock:
        return _session_active


def _set_session(*, active: bool) -> None:
    global _session_active
    with _session_lock:
        _session_active = active


def _get_charging_vehicles(
    apis: list[tuple[VehicleConfig, TeslaAPI]],
) -> list[tuple[VehicleConfig, TeslaAPI, dict]]:
    """Return (vehicle, api, vehicle_data) tuples for all actively charging vehicles."""
    return overload_handler._get_charging_vehicles(apis)  # noqa: SLF001


def _get_consumption(em_ctrl: EnergyMonitorController, app_config: AppConfig) -> float:
    """Return current net grid exchange in amps (negative = exporting)."""
    return overload_handler._get_consumption(em_ctrl, app_config)  # noqa: SLF001


def _apply_solar_adjustment(
    charging: list[tuple[VehicleConfig, TeslaAPI, dict]],
    em_amps: float,
    cfg: SystemConfig,
) -> bool:
    """
    Apply one adjustment iteration toward ``solarTargetAmps``.

    A positive ``em_amps`` is an import (too much) and reduces charging; a
    negative ``em_amps`` is an export (surplus) and raises charging to absorb
    it.  Each vehicle's delta is proportional to its current draw, clamped to
    its [min, max] range, floors to an integer amp and only issues a command
    when the integer value actually changes — so a balanced grid issues nothing.

    Returns True if at least one vehicle's limit was changed.
    """
    target = cfg.solarTargetAmps

    total_current = sum(
        float(d["charge_state"]["charger_actual_current"]) for _, _, d in charging
    )
    if total_current <= 0:
        return False

    delta = target - em_amps  # >0 = surplus to absorb, <0 = import to shave
    if abs(delta) < _DEADBAND_AMPS:
        return False

    changed = False
    for vehicle, api, data in charging:
        current = float(data["charge_state"]["charger_actual_current"])
        share = delta * (current / total_current)
        new_limit = math.floor(current + share)
        new_limit = max(
            int(vehicle.chargerMinAmps), min(new_limit, int(vehicle.chargerMaxAmps))
        )
        if new_limit == math.floor(current):
            continue
        try:
            api.set_charge_amp_limit(new_limit)
            tsc_logger.info(
                "Solar adjust %s: %.0fA → %dA (grid %.1fA, target %.1fA)",
                vehicle.name or vehicle.id,
                current,
                new_limit,
                em_amps,
                target,
            )
            changed = True
        except HTTPException:
            tsc_logger.exception("Failed to adjust charge limit for %s", vehicle.id)
    return changed


def trigger_solar(app_config: AppConfig) -> tuple[bool, str]:
    """
    Attempt to start a solar surplus handling session.

    Returns ``(True, message)`` if a session was started,
    ``(False, reason)`` if it was not.
    """
    if is_surplus_active():
        return False, "solar session already active"

    if overload_handler.is_session_active():
        return False, "overload session active"

    if not app_config.system.solarSurplusEnabled:
        return False, "solar surplus mode not enabled"

    if not app_config.vehicles:
        return False, "no vehicles configured"

    apis = [(v, TeslaAPI(v)) for v in app_config.vehicles if v.enabled]
    charging = _get_charging_vehicles(apis)
    if not charging:
        return False, "no vehicles are currently charging"

    t = threading.Thread(
        target=handle_solar,
        args=(app_config,),
        name="tsc_solar_handler_thread",
        daemon=True,
    )
    t.start()
    return True, "solar handler session started"


def _solar_iteration(
    app_config: AppConfig,
    em_ctrl: EnergyMonitorController,
    session_start: float,
    no_change_count: int,
) -> int | None:
    """Run one adjustment pass. Return next ``no_change_count``, or None to end."""
    cfg = app_config.system

    for condition, msg in (
        (
            not cfg.solarSurplusEnabled,
            "Solar surplus mode disabled — ending session.",
        ),
        (
            overload_handler.is_session_active(),
            "Overload session started — yielding.",
        ),
        (
            time.time() - session_start > _SOLAR_MAX_SECONDS,
            "Solar session max duration reached — ending session.",
        ),
    ):
        if condition:
            tsc_logger.info(msg)
            return None

    apis = [(v, TeslaAPI(v)) for v in app_config.vehicles if v.enabled]
    charging = _get_charging_vehicles(apis)
    if not charging:
        tsc_logger.info("No vehicles actively charging — ending session.")
        return None

    em_amps = _get_consumption(em_ctrl, app_config)
    if em_amps == 0.0 or em_amps > cfg.homeMaxAmps:
        if em_amps == 0.0:
            tsc_logger.warning("Consumption read returned 0 — ending session.")
        else:
            tsc_logger.warning(
                "Grid consumption %.2fA exceeds homeMaxAmps %.2fA — "
                "deferring to the overload handler.",
                em_amps,
                cfg.homeMaxAmps,
            )
        return None

    changed = _apply_solar_adjustment(charging, em_amps, cfg)
    if changed:
        return 0
    next_count = no_change_count + 1
    if next_count < _STABLE_NEEDED:
        return next_count
    tsc_logger.info("No adjustments needed — ending solar session.")
    return None


def handle_solar(app_config: AppConfig) -> None:
    """
    Solar surplus supervisor — runs in a dedicated thread.

    Loops every ``sleepTimeSecs`` adjusting charging current until the grid is
    balanced (or every vehicle is pinned at a limit and nothing changes).
    The session flag is always cleared in a finally block, even on error.
    """
    _set_session(active=True)
    session_start = time.time()
    no_change_count = 0
    tsc_logger.info("Solar handler session started.")

    try:
        cfg = app_config.system
        try:
            em_ctrl = _em_controller.create_energy_monitor_controller(
                cfg.energyMonitorType, cfg.energyMonitorIp
            )
        except ValueError:
            tsc_logger.exception(
                "Invalid energy monitor type '%s'.", cfg.energyMonitorType
            )
            return

        while True:
            cfg = app_config.system  # always act on fresh config
            result = _solar_iteration(
                app_config, em_ctrl, session_start, no_change_count
            )
            if result is None:
                break
            no_change_count = result
            time.sleep(cfg.sleepTimeSecs)

    # Deliberately broad: this is the thread's top-level guard — any
    # unexpected error must be logged, not crash the thread silently.
    except Exception:
        tsc_logger.exception("Unhandled error in solar handler")
    finally:
        _set_session(active=False)
        tsc_logger.info("Solar handler session ended.")
