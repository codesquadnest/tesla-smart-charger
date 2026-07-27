"""Unit tests for the per-vehicle telemetry cache."""

import time

import pytest

from tesla_smart_charger import telemetry_cache
from tesla_smart_charger.models import VehicleConfig
from tesla_smart_charger.tesla_api import TeslaAPI


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Keep the module-level cache from leaking between tests."""
    telemetry_cache.reset()


def _vehicle() -> VehicleConfig:
    return VehicleConfig(
        id="veh-1",
        name="Model Y",
        vin="5YJYGDEE1MF000001",
        teslaVehicleId="777",
        enabled=True,
    )


def test_age_is_none_for_unknown_vehicle() -> None:
    """age() returns None when a vehicle has never been fetched."""
    assert telemetry_cache.age("nope") is None


def test_disabled_vehicle_is_not_fetched() -> None:
    """A disabled vehicle short-circuits without scheduling a refresh."""
    vehicle = _vehicle()
    vehicle.enabled = False

    status = telemetry_cache.get(vehicle, overload_active=False)

    assert status.online is False
    assert status.telemetryAgeSecs is None
    assert telemetry_cache.is_refreshing(vehicle.id) is False


def test_get_returns_a_copy_not_the_cached_instance() -> None:
    """
    Mutating a returned status must not corrupt the cache.

    The cached instance is shared with the background refresh thread and every
    other caller, so `get` has to hand out copies.
    """
    vehicle = _vehicle()
    cached = telemetry_cache.base_status(vehicle)
    cached.online = True
    cached.batteryLevel = 55
    telemetry_cache._cache[vehicle.id] = (time.monotonic(), cached)

    first = telemetry_cache.get(vehicle, overload_active=False)
    first.batteryLevel = 999

    second = telemetry_cache.get(vehicle, overload_active=False)
    assert second.batteryLevel == 55
    assert cached.batteryLevel == 55
    assert cached.telemetryAgeSecs is None


def test_get_stamps_freshness_on_cached_entry() -> None:
    """A cache hit is stamped with a non-negative age."""
    vehicle = _vehicle()
    cached = telemetry_cache.base_status(vehicle)
    cached.online = True
    telemetry_cache._cache[vehicle.id] = (time.monotonic(), cached)

    status = telemetry_cache.get(vehicle, overload_active=False)

    assert status.telemetryAgeSecs is not None
    assert status.telemetryAgeSecs >= 0


def test_invalidate_drops_the_entry() -> None:
    """invalidate() removes a cached entry so the next read refetches."""
    vehicle = _vehicle()
    telemetry_cache._cache[vehicle.id] = (
        time.monotonic(),
        telemetry_cache.base_status(vehicle),
    )

    telemetry_cache.invalidate(vehicle.id)

    assert telemetry_cache.age(vehicle.id) is None


def test_superseded_refresh_is_discarded_and_refetched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A fetch that started before invalidate() must not repopulate the cache.

    Without this the pre-command telemetry lands after the command, is stamped
    fresh, and the dashboard shows the old value for a whole TTL.
    """
    vehicle = _vehicle()
    monkeypatch.setattr(
        TeslaAPI,
        "get_vehicle_data",
        lambda self: {  # noqa: ARG005
            "state": "online",
            "charge_state": {"charge_limit_soc": 80},
        },
    )
    refetched: list[str] = []
    monkeypatch.setattr(
        telemetry_cache, "schedule_refresh", lambda v: refetched.append(v.id)
    )

    generation = telemetry_cache._generation.get(vehicle.id, 0)
    telemetry_cache.invalidate(vehicle.id)
    telemetry_cache._refresh(vehicle, generation)

    assert telemetry_cache.age(vehicle.id) is None
    assert refetched == [vehicle.id]
    assert telemetry_cache.is_refreshing(vehicle.id) is False


def test_current_generation_refresh_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """A refresh nothing invalidated under it caches its result as normal."""
    vehicle = _vehicle()
    monkeypatch.setattr(
        TeslaAPI,
        "get_vehicle_data",
        lambda self: {  # noqa: ARG005
            "state": "online",
            "charge_state": {"charge_limit_soc": 90},
        },
    )

    telemetry_cache._refresh(vehicle, telemetry_cache._generation.get(vehicle.id, 0))

    status = telemetry_cache.get(vehicle, overload_active=False)
    assert status.chargeLimitSoc == 90
    assert status.online is True


def test_schedule_refresh_captures_current_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The generation is read at schedule time, not when the fetch completes."""
    captured: list[int] = []

    class _FakeThread:
        def __init__(self, **kwargs: object) -> None:
            captured.append(kwargs["args"][1])

        def start(self) -> None:
            pass

    monkeypatch.setattr(telemetry_cache.threading, "Thread", _FakeThread)

    vehicle = _vehicle()
    telemetry_cache.invalidate(vehicle.id)
    telemetry_cache.invalidate(vehicle.id)
    telemetry_cache.schedule_refresh(vehicle)

    assert captured == [2]


def test_schedule_refresh_dedupes(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second schedule_refresh is a no-op while one is already in flight."""
    started: list[str] = []

    def _fake_thread_start(self: object) -> None:  # noqa: ARG001
        started.append("started")

    monkeypatch.setattr("threading.Thread.start", _fake_thread_start)

    vehicle = _vehicle()
    assert telemetry_cache.schedule_refresh(vehicle) is True
    assert telemetry_cache.schedule_refresh(vehicle) is False
    assert len(started) == 1
