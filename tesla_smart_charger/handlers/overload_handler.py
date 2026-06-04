"""Handles overload events — supports single or multiple charging vehicles."""

import math
import threading
import time
from typing import List, Optional, Tuple

from fastapi import HTTPException

from tesla_smart_charger import constants, logger
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.controllers import db_controller
from tesla_smart_charger.controllers import em_controller as _em_controller
from tesla_smart_charger.models import OverloadStrategy, VehicleConfig
from tesla_smart_charger.tesla_api import TeslaAPI

tsc_logger = logger.get_logger()

# Lock that guards the overload session flag
_session_lock = threading.Lock()
_session_active = False


def is_session_active() -> bool:
    with _session_lock:
        return _session_active


def _set_session(active: bool) -> None:
    global _session_active
    with _session_lock:
        _session_active = active


# ─── Database helpers ──────────────────────────────────────────────────────────

def _init_db() -> Optional[object]:
    try:
        ctrl = db_controller.create_database_controller(
            constants.DB_TYPE, constants.DB_NAME, constants.DB_FILE_PATH
        )
        ctrl.initialize_db()
        return ctrl
    except Exception as exc:
        tsc_logger.error("Failed to initialise DB controller: %s", exc)
        return None


def _save_event(start_time: str, vehicle_id: Optional[str] = None) -> None:
    ctrl = _init_db()
    if ctrl is None:
        return
    end_time = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        s = time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
        e = time.mktime(time.strptime(end_time, "%Y-%m-%d %H:%M:%S"))
        duration = str(e - s)
    except ValueError:
        duration = "0"
    try:
        ctrl.insert_data(
            {
                "start": start_time,
                "end": end_time,
                "duration": duration,
                "vehicle_id": vehicle_id or "",
            }
        )
        tsc_logger.info("Overload event saved to database.")
    except Exception as exc:
        tsc_logger.error("Error saving overload event: %s", exc)
    finally:
        try:
            ctrl.close_connection()
        except Exception:
            pass


# ─── Calculation helpers ───────────────────────────────────────────────────────

def _calculate_new_charge_limit(
    current_charge_limit: float,
    current_em_consumption: float,
    max_charge_limit: float,
    min_charge_limit: float,
    home_max_amps: float,
) -> int:
    """
    Compute the adjusted charge limit for a vehicle.

    Reduces by the difference between current consumption and the home limit,
    clamped to [min_charge_limit, max_charge_limit].
    """
    excess = current_em_consumption - home_max_amps
    new_limit = current_charge_limit - excess

    new_limit = max(min_charge_limit, min(new_limit, max_charge_limit))

    tsc_logger.debug(
        "Charge limit: %.1f → %.1f  (em=%.2f, max=%.1f, excess=%.2f)",
        current_charge_limit,
        new_limit,
        current_em_consumption,
        home_max_amps,
        excess,
    )
    return math.floor(new_limit)


def _get_consumption(em_ctrl, app_config: AppConfig) -> float:
    """Return current consumption in amps, 0.0 on error."""
    voltage = app_config.system.voltage
    try:
        watts = em_ctrl.get_consumption()
        amps = float(watts) / voltage
        tsc_logger.debug("Current consumption: %.2f A (%.1f W / %.0f V)", amps, watts, voltage)
        return amps
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        tsc_logger.error("Error reading consumption: %s", exc)
        return 0.0


# ─── Multi-vehicle overload strategies ────────────────────────────────────────

def _get_charging_vehicles(
    apis: List[Tuple[VehicleConfig, TeslaAPI]]
) -> List[Tuple[VehicleConfig, TeslaAPI, dict]]:
    """Return (vehicle, api, vehicle_data) tuples for all actively charging vehicles."""
    charging = []
    for vehicle, api in apis:
        if not vehicle.enabled:
            continue
        try:
            data = api.get_vehicle_data()
        except HTTPException:
            tsc_logger.warning("Could not fetch data for vehicle %s — skipping.", vehicle.id)
            continue
        if (
            data.get("state") == "online"
            and data.get("charge_state", {}).get("charging_state") == "Charging"
        ):
            charging.append((vehicle, api, data))
    return charging


def _apply_proportional(
    charging: List[Tuple[VehicleConfig, TeslaAPI, dict]],
    em_amps: float,
    home_max_amps: float,
) -> bool:
    """
    Reduce each charging vehicle proportionally to clear the overload.

    Returns True if at least one vehicle's limit was changed.
    """
    if not charging:
        return False
    changed = False
    num = len(charging)
    for vehicle, api, data in charging:
        current = float(data["charge_state"]["charger_actual_current"])
        new_limit = _calculate_new_charge_limit(
            current,
            em_amps,
            vehicle.chargerMaxAmps,
            vehicle.chargerMinAmps,
            home_max_amps / num,  # each vehicle "owns" a slice of the budget
        )
        if new_limit != math.floor(current):
            try:
                api.set_charge_amp_limit(new_limit)
                changed = True
            except HTTPException as exc:
                tsc_logger.error(
                    "Failed to set charge limit for %s: %s", vehicle.id, exc
                )
    return changed


def _apply_priority(
    charging: List[Tuple[VehicleConfig, TeslaAPI, dict]],
    em_amps: float,
    home_max_amps: float,
) -> bool:
    """
    Reduce vehicles one at a time in reverse priority order
    (lowest priority → highest priority) until overload is resolved.

    Returns True if at least one vehicle's limit was changed.
    """
    # Sort ascending priority number: higher number = lower priority = reduce first
    sorted_charging = sorted(charging, key=lambda x: -x[0].priority)
    remaining_excess = em_amps - home_max_amps
    changed = False

    for vehicle, api, data in sorted_charging:
        if remaining_excess <= 0:
            break
        current = float(data["charge_state"]["charger_actual_current"])
        # How much can we reduce this vehicle?
        reducible = current - vehicle.chargerMinAmps
        reduction = min(reducible, remaining_excess)
        new_limit = math.floor(current - reduction)
        new_limit = max(int(vehicle.chargerMinAmps), new_limit)

        if new_limit != math.floor(current):
            try:
                api.set_charge_amp_limit(new_limit)
                remaining_excess -= reduction
                changed = True
            except HTTPException as exc:
                tsc_logger.error(
                    "Failed to set charge limit for %s: %s", vehicle.id, exc
                )
    return changed


# ─── Public trigger (called by em_cron and the /overload HTTP endpoint) ────────

def trigger_overload(app_config: AppConfig) -> Tuple[bool, str]:
    """
    Attempt to start an overload handling session.

    Applies an initial downstep to all charging vehicles then spawns the
    supervised ``handle_overload`` thread.

    Returns ``(True, message)`` if a session was started,
    ``(False, reason)`` if it was not.
    """
    if is_session_active():
        return False, "overload handling session already active"

    if not app_config.vehicles:
        return False, "no vehicles configured"

    cfg = app_config.system
    initial_applied = False

    for vehicle in app_config.vehicles:
        if not vehicle.enabled:
            continue
        try:
            api = TeslaAPI(vehicle)
            data = api.get_vehicle_data()
        except HTTPException:
            continue

        if (
            data.get("state") == "online"
            and data.get("charge_state", {}).get("charging_state") == "Charging"
        ):
            current = float(data["charge_state"]["charger_actual_current"])
            new_limit = round(current * cfg.downStepPercentage)
            new_limit = max(int(vehicle.chargerMinAmps), new_limit)
            try:
                api.set_charge_amp_limit(new_limit)
                initial_applied = True
            except HTTPException as exc:
                tsc_logger.error("Initial downstep failed for %s: %s", vehicle.id, exc)

    if not initial_applied:
        return False, "no vehicles are currently charging"

    t = threading.Thread(
        target=handle_overload,
        args=(app_config,),
        name="tsc_handle_overload_thread",
        daemon=True,
    )
    t.start()
    return True, "overload handler session started"


# ─── Main overload handler ────────────────────────────────────────────────────

def handle_overload(app_config: AppConfig) -> None:
    """
    Top-level overload handler — runs in a dedicated thread.

    Reads the current overload strategy from AppConfig and applies it
    to all actively-charging vehicles.  Logs the event to the database.
    The session flag is always cleared in a finally block, even on error.
    """
    _set_session(True)
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
    tsc_logger.info("Overload handler started. Supervised session begun.")

    # Keep a reference to the last known charging set so _save_event can use it
    charging: List[Tuple[VehicleConfig, TeslaAPI, dict]] = []

    try:
        # Build (VehicleConfig, TeslaAPI) pairs for every enabled vehicle
        apis: List[Tuple[VehicleConfig, TeslaAPI]] = [
            (v, TeslaAPI(v)) for v in app_config.vehicles if v.enabled
        ]

        cfg = app_config.system

        # Instantiate energy monitor
        try:
            em_ctrl = _em_controller.create_energy_monitor_controller(
                cfg.energyMonitorType, cfg.energyMonitorIp
            )
        except ValueError:
            tsc_logger.error("Invalid energy monitor type '%s'.", cfg.energyMonitorType)
            return

        # ── Stabilisation phase ──────────────────────────────────────────────
        # Wait up to 10 × sleep_time for consumption to stabilise after first step
        for _ in range(10):
            time.sleep(cfg.sleepTimeSecs)
            cfg = app_config.system  # refresh
            em_amps = _get_consumption(em_ctrl, app_config)
            if em_amps > cfg.homeMaxAmps:
                tsc_logger.info("Overload still present after stabilisation wait.")
                break

        # ── Supervised adjustment loop ───────────────────────────────────────
        no_change_count = 0

        while True:
            cfg = app_config.system  # always act on fresh config

            # Refresh vehicle API references in case tokens were updated
            apis = [(v, TeslaAPI(v)) for v in app_config.vehicles if v.enabled]

            charging = _get_charging_vehicles(apis)
            if not charging:
                tsc_logger.info("No vehicles actively charging — ending session.")
                break

            em_amps = _get_consumption(em_ctrl, app_config)
            if em_amps == 0.0:
                tsc_logger.warning("Consumption read returned 0 — ending session.")
                break

            if em_amps <= cfg.homeMaxAmps:
                tsc_logger.info(
                    "Consumption within limits (%.2fA ≤ %.2fA) — ending session.",
                    em_amps,
                    cfg.homeMaxAmps,
                )
                break

            if no_change_count >= constants.MAX_QUERIES:
                tsc_logger.info(
                    "No change for %d consecutive iterations — ending session.",
                    no_change_count,
                )
                break

            # Check whether all vehicles are already at minimum before applying
            all_at_min = all(
                float(d["charge_state"]["charger_actual_current"]) <= v.chargerMinAmps
                for v, _, d in charging
            )
            if all_at_min:
                tsc_logger.info("All vehicles at minimum charge limit — ending session.")
                break

            strategy = cfg.overloadStrategy
            tsc_logger.info(
                "Applying %s strategy | em=%.2fA | home_max=%.2fA | vehicles=%d",
                strategy,
                em_amps,
                cfg.homeMaxAmps,
                len(charging),
            )

            if strategy == OverloadStrategy.PRIORITY:
                changed = _apply_priority(charging, em_amps, cfg.homeMaxAmps)
            else:
                changed = _apply_proportional(charging, em_amps, cfg.homeMaxAmps)

            # Only count iterations where no adjustment could be made
            if not changed:
                no_change_count += 1
            else:
                no_change_count = 0  # reset on successful adjustment

            time.sleep(cfg.sleepTimeSecs)

    except Exception as exc:
        tsc_logger.error("Unhandled error in overload handler: %s", exc)
    finally:
        # Always persist the event and release the session lock
        first_vid = charging[0][0].id if charging else None
        _save_event(start_time, first_vid)
        _set_session(False)
        tsc_logger.info("Overload handler finished. Supervised session ended.")
