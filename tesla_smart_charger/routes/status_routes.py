"""GET /api/v1/status — overall system health and live state."""

import time
import threading
from typing import Callable, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tesla_smart_charger import logger
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.models import SystemStatus, VehicleStatus
from tesla_smart_charger.tesla_api import TeslaAPI

tsc_logger = logger.get_logger()

router = APIRouter(prefix="/api/v1", tags=["status"])

# References injected by __main__
_app_config: Optional[AppConfig] = None
_monitor_active: bool = False
_overload_active_fn: Optional[Callable[[], bool]] = None

# ─── Per-vehicle telemetry cache ───────────────────────────────────────────────
# Stores (timestamp, VehicleStatus) per vehicle id.  Entries are served from
# cache until they are older than _CACHE_TTL_SECS seconds.
_CACHE_TTL_SECS = 30
_cache: Dict[str, tuple] = {}          # vehicle_id → (fetched_at, VehicleStatus)
_cache_lock = threading.Lock()


def init(app_config: AppConfig, monitor_active_fn, overload_active_fn) -> None:
    global _app_config, _monitor_active, _overload_active_fn
    _app_config = app_config
    _monitor_active = monitor_active_fn
    _overload_active_fn = overload_active_fn


def _live_vehicle_status(vehicle) -> VehicleStatus:
    """
    Return live telemetry for a vehicle.

    Results are cached for ``_CACHE_TTL_SECS`` seconds to avoid hammering
    the Tesla API on every dashboard refresh.
    """
    base = VehicleStatus(
        id=vehicle.id,
        name=vehicle.name,
        vin=vehicle.vin,
        teslaVehicleId=vehicle.teslaVehicleId,
        teslaHttpProxy=vehicle.teslaHttpProxy,
        chargerMaxAmps=vehicle.chargerMaxAmps,
        chargerMinAmps=vehicle.chargerMinAmps,
        priority=vehicle.priority,
        enabled=vehicle.enabled,
        online=False,
    )
    if not vehicle.enabled or not vehicle.teslaVehicleId:
        return base

    # Serve from cache when the entry is still fresh
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(vehicle.id)
        if cached is not None:
            fetched_at, cached_status = cached
            if now - fetched_at < _CACHE_TTL_SECS:
                return cached_status

    # Cache miss (or stale) — fetch live data
    try:
        api = TeslaAPI(vehicle)
        data = api.get_vehicle_data()
        base.online = data.get("state") == "online"
        charge = data.get("charge_state", {})
        base.chargingState = charge.get("charging_state")
        base.chargerActualCurrent = charge.get("charger_actual_current")
        base.batteryLevel = charge.get("battery_level")
    except Exception:
        pass  # fall back to the offline baseline

    with _cache_lock:
        _cache[vehicle.id] = (now, base)

    return base


@router.get("/status", response_model=SystemStatus)
def get_status() -> JSONResponse:
    """Return overall system status including live vehicle states."""
    if _app_config is None:
        return JSONResponse({"error": "Not initialised"}, status_code=503)

    cfg = _app_config.system
    vehicle_statuses = [_live_vehicle_status(v) for v in _app_config.vehicles]

    status = SystemStatus(
        configured=cfg.configured,
        monitorActive=_monitor_active() if callable(_monitor_active) else _monitor_active,
        overloadActive=_overload_active_fn() if callable(_overload_active_fn) else False,
        homeMaxAmps=cfg.homeMaxAmps,
        region=cfg.region.value,
        voltage=cfg.voltage,
        vehicles=vehicle_statuses,
    )
    return JSONResponse(status.model_dump(), status_code=200)
