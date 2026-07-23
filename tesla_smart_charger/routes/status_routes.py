"""GET /api/v1/status — overall system health and live state."""

import threading
import time
from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tesla_smart_charger import logger
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.cron import em_cron
from tesla_smart_charger.models import SystemStatus, VehicleConfig, VehicleStatus
from tesla_smart_charger.tesla_api import TeslaAPI

tsc_logger = logger.get_logger()

router = APIRouter(prefix="/api/v1", tags=["status"])

# References injected by __main__
_app_config: AppConfig | None = None
_monitor_active: bool = False
_overload_active_fn: Callable[[], bool] | None = None

# ─── Per-vehicle telemetry cache ───────────────────────────────────────────────
# Stores (timestamp, VehicleStatus) per vehicle id.  Entries are served from
# cache until they are older than the TTL.  Offline vehicles get a longer TTL
# so we don't spam the Tesla API waking them up every 30 seconds.
_CACHE_TTL_ONLINE_SECS = 30
_CACHE_TTL_OFFLINE_SECS = 300  # 5 min
_cache: dict[str, tuple] = {}  # vehicle_id → (fetched_at, VehicleStatus)
_cache_lock = threading.Lock()

# vehicle ids with a background refresh currently in flight — prevents piling
# up duplicate Tesla API calls for the same vehicle while one is already running.
_pending: set = set()
_pending_lock = threading.Lock()


def init(
    app_config: AppConfig,
    monitor_active_fn: Callable[[], bool],
    overload_active_fn: Callable[[], bool],
) -> None:
    """Inject the shared AppConfig and state-check callbacks used by this router."""
    global _app_config, _monitor_active, _overload_active_fn
    _app_config = app_config
    _monitor_active = monitor_active_fn
    _overload_active_fn = overload_active_fn


def _base_vehicle_status(vehicle: VehicleConfig) -> VehicleStatus:
    return VehicleStatus(
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


def _refresh_vehicle_status(vehicle: VehicleConfig) -> None:
    """
    Fetch live telemetry for a vehicle and update the cache.

    Runs on a background thread so it never blocks a request.
    """
    status = _base_vehicle_status(vehicle)
    try:
        api = TeslaAPI(vehicle)
        data = api.get_vehicle_data()
        status.online = data.get("state") == "online"
        charge = data.get("charge_state", {})
        status.chargingState = charge.get("charging_state")
        status.chargerActualCurrent = charge.get("charger_actual_current")
        status.batteryLevel = charge.get("battery_level")
    # Deliberately broad: this runs on a background thread and must never
    # crash — `finally` below always caches a result either way.
    except Exception:
        tsc_logger.exception("Live telemetry fetch failed for vehicle %s", vehicle.id)
    finally:
        with _cache_lock:
            _cache[vehicle.id] = (time.monotonic(), status)
        with _pending_lock:
            _pending.discard(vehicle.id)


def _live_vehicle_status(vehicle: VehicleConfig) -> VehicleStatus:
    """
    Return the best currently-known telemetry for a vehicle.

    Never blocks on the network: serves cached data (fresh or stale)
    immediately, kicking off a background refresh whenever the cache entry
    is missing or has expired. Callers always get an instant response; a
    stale/placeholder result is replaced in the cache the next time this
    endpoint is polled once the background fetch completes.
    """
    base = _base_vehicle_status(vehicle)
    if not vehicle.enabled or not vehicle.teslaVehicleId:
        return base

    # Offline vehicles get a longer TTL to avoid waking them unnecessarily.
    # During an active overload session we use the shorter online TTL even for
    # offline vehicles so the dashboard reflects live charge-limit changes sooner.
    overload_active = _overload_active_fn() if callable(_overload_active_fn) else False
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(vehicle.id)
        if cached is not None:
            fetched_at, cached_status = cached
            ttl = (
                _CACHE_TTL_ONLINE_SECS
                if (cached_status.online or overload_active)
                else _CACHE_TTL_OFFLINE_SECS
            )
            is_fresh = now - fetched_at < ttl
        else:
            is_fresh = False

    if cached is not None and is_fresh:
        return cached_status

    # Cache is missing or stale — kick off a background refresh (unless one
    # is already in flight) and return the best data we have right now.
    with _pending_lock:
        already_pending = vehicle.id in _pending
        if not already_pending:
            _pending.add(vehicle.id)
    if not already_pending:
        threading.Thread(
            target=_refresh_vehicle_status, args=(vehicle,), daemon=True
        ).start()

    if cached is not None:
        return cached_status

    base.pending = True
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
        monitorActive=_monitor_active()
        if callable(_monitor_active)
        else _monitor_active,
        overloadActive=_overload_active_fn()
        if callable(_overload_active_fn)
        else False,
        currentConsumptionAmps=em_cron.LAST_CONSUMPTION_AMPS,
        homeMaxAmps=cfg.homeMaxAmps,
        region=cfg.region.value,
        voltage=cfg.voltage,
        vehicles=vehicle_statuses,
    )
    return JSONResponse(status.model_dump(), status_code=200)
