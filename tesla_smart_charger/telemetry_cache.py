"""
Per-vehicle telemetry cache.

Shared by the status route (which reads it) and the command routes (which
invalidate it after a command changes vehicle state).  Reads never block on
the network: cached data is served immediately — fresh or stale — while a
background thread refreshes expired entries.
"""

import threading
import time

from tesla_smart_charger import logger
from tesla_smart_charger.models import VehicleConfig, VehicleStatus
from tesla_smart_charger.tesla_api import TeslaAPI

tsc_logger = logger.get_logger()

# Entries are served from cache until they are older than the TTL.  Offline
# vehicles get a longer TTL so we don't spam the Tesla API waking them up
# every 30 seconds.
_CACHE_TTL_ONLINE_SECS = 30
_CACHE_TTL_OFFLINE_SECS = 300  # 5 min

_cache: dict[str, tuple] = {}  # vehicle_id → (fetched_at, VehicleStatus)
# Bumped by invalidate().  A refresh captures the generation it started under
# and discards its result if that number moved while it was in flight —
# otherwise a fetch begun *before* a command would land *after* it and
# repopulate the cache with pre-command telemetry, silently undoing the
# invalidation for a full TTL.
_generation: dict[str, int] = {}  # vehicle_id → epoch
_cache_lock = threading.Lock()  # guards both _cache and _generation

# vehicle ids with a background refresh currently in flight — prevents piling
# up duplicate Tesla API calls for the same vehicle while one is already running.
_pending: set = set()
_pending_lock = threading.Lock()


def base_status(vehicle: VehicleConfig) -> VehicleStatus:
    """Return a status carrying only the vehicle's configured fields."""
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


def invalidate(vehicle_id: str) -> None:
    """
    Drop a vehicle's cached telemetry so the next read refetches it.

    Also supersedes any refresh already in flight, whose data predates whatever
    prompted the invalidation.
    """
    with _cache_lock:
        _cache.pop(vehicle_id, None)
        _generation[vehicle_id] = _generation.get(vehicle_id, 0) + 1


def age(vehicle_id: str) -> float | None:
    """Seconds since this vehicle's telemetry was fetched, or None if never."""
    with _cache_lock:
        cached = _cache.get(vehicle_id)
    if cached is None:
        return None
    return time.monotonic() - cached[0]


def is_refreshing(vehicle_id: str) -> bool:
    """Whether a background refresh is currently in flight for this vehicle."""
    with _pending_lock:
        return vehicle_id in _pending


def reset() -> None:
    """Clear all cached telemetry, generations and pending markers."""
    with _cache_lock:
        _cache.clear()
        _generation.clear()
    with _pending_lock:
        _pending.clear()


def _refresh(vehicle: VehicleConfig, generation: int) -> None:
    """
    Fetch live telemetry for a vehicle and update the cache.

    Runs on a background thread so it never blocks a request.  *generation* is
    the epoch this refresh started under; if `invalidate` moved it meanwhile,
    the result is stale-on-arrival and gets dropped rather than cached.
    """
    status = base_status(vehicle)
    try:
        api = TeslaAPI(vehicle)
        data = api.get_vehicle_data()
        status.online = data.get("state") == "online"
        charge = data.get("charge_state", {})
        status.chargingState = charge.get("charging_state")
        status.chargerActualCurrent = charge.get("charger_actual_current")
        status.batteryLevel = charge.get("battery_level")
        status.chargeLimitSoc = charge.get("charge_limit_soc")
    # Deliberately broad: this runs on a background thread and must never
    # crash — `finally` below always settles the cache either way.
    except Exception:
        tsc_logger.exception("Live telemetry fetch failed for vehicle %s", vehicle.id)
    finally:
        with _cache_lock:
            superseded = _generation.get(vehicle.id, 0) != generation
            if not superseded:
                _cache[vehicle.id] = (time.monotonic(), status)
        # Cleared before any re-schedule below, which would otherwise dedupe
        # itself away against this very refresh.
        with _pending_lock:
            _pending.discard(vehicle.id)
        if superseded:
            tsc_logger.debug(
                "Discarding superseded telemetry for vehicle %s; refetching.",
                vehicle.id,
            )
            # Bounded: only an explicit invalidate() bumps the generation, so
            # this can't spin on its own.
            schedule_refresh(vehicle)


def schedule_refresh(vehicle: VehicleConfig) -> bool:
    """
    Start a background telemetry refresh unless one is already in flight.

    Returns True when a new refresh thread was started.
    """
    with _pending_lock:
        already_pending = vehicle.id in _pending
        if not already_pending:
            _pending.add(vehicle.id)
    if already_pending:
        return False
    with _cache_lock:
        generation = _generation.get(vehicle.id, 0)
    threading.Thread(target=_refresh, args=(vehicle, generation), daemon=True).start()
    return True


def _with_freshness(vehicle_id: str, status: VehicleStatus) -> VehicleStatus:
    """
    Return a copy of *status* stamped with its current freshness.

    Always copies: the cached instance is shared with the background refresh
    thread and with every other caller, so mutating it in place would corrupt
    the cache.  Age is computed server-side because the stored timestamp is a
    ``time.monotonic()`` value — process-relative and meaningless to a client.
    """
    return status.model_copy(
        update={
            "telemetryAgeSecs": age(vehicle_id),
            "refreshing": is_refreshing(vehicle_id),
        }
    )


def get(vehicle: VehicleConfig, *, overload_active: bool) -> VehicleStatus:
    """
    Return the best currently-known telemetry for a vehicle.

    Never blocks on the network: serves cached data (fresh or stale)
    immediately, kicking off a background refresh whenever the cache entry
    is missing or has expired.
    """
    base = base_status(vehicle)
    if not vehicle.enabled or not vehicle.teslaVehicleId:
        return base

    # During an active overload session we use the shorter online TTL even for
    # offline vehicles so the dashboard reflects live charge-limit changes sooner.
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
        return _with_freshness(vehicle.id, cached_status)

    # Cache is missing or stale — kick off a background refresh (unless one is
    # already in flight) and return the best data we have right now.  `refreshing`
    # is read after this so a just-started refresh is reported in this response.
    schedule_refresh(vehicle)

    if cached is not None:
        return _with_freshness(vehicle.id, cached_status)

    base.pending = True
    return _with_freshness(vehicle.id, base)
