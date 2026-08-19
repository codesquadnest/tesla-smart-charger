"""
Integration-level tests for the vehicle command endpoints.

Each test builds an isolated AppConfig in a temporary directory and injects it
into the route modules directly.  TeslaAPI is always monkeypatched — no real
Tesla calls are made, and no background telemetry threads are allowed to start.

Every command route sits behind `security.require_auth`, so tests either send
`auth=CREDS` or assert the guard rejects them.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tesla_smart_charger import security, telemetry_cache
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.routes import command_routes, vehicle_routes
from tesla_smart_charger.tesla_api import TeslaAPI

VEHICLE_PAYLOAD = {
    "name": "Model Y",
    "vin": "5YJYGDEE1MF000001",
    "teslaVehicleId": "777",
    "teslaAccessToken": "at_test",
    "teslaRefreshToken": "rt_test",
    "teslaHttpProxy": "http://localhost:4443",
    "teslaClientId": "cid_test",
    "chargerMaxAmps": 32.0,
    "chargerMinAmps": 6.0,
    "priority": 1,
    "enabled": True,
}

USERNAME = "tsc-admin"
PASSWORD = "correct-horse-battery"
CREDS = (USERNAME, PASSWORD)


@pytest.fixture(autouse=True)
def _clear_module_state() -> None:
    """Keep the module-level telemetry cache and auth wiring from leaking."""
    telemetry_cache.reset()
    security._app_config = None


def _make_app(
    tmp_path: Path, *, auth_enabled: bool = True
) -> tuple[FastAPI, AppConfig]:
    """Build a minimal FastAPI app wired to a fresh AppConfig in tmp_path."""
    app_cfg = AppConfig(str(tmp_path / "config"))
    app_cfg._legacy_file = tmp_path / "no_legacy.json"
    app_cfg.load()
    if auth_enabled:
        app_cfg.update_system(
            {
                "auth": {
                    "enabled": True,
                    "username": USERNAME,
                    "passwordHash": security.hash_password(PASSWORD),
                }
            }
        )

    app = FastAPI()
    security.init(app_cfg)
    vehicle_routes.init(app_cfg)
    command_routes.init(app_cfg)
    app.include_router(vehicle_routes.router)
    app.include_router(command_routes.router)
    return app, app_cfg


def _client_with_vehicle(
    tmp_path: Path, *, auth_enabled: bool = True
) -> tuple[TestClient, str]:
    app, _ = _make_app(tmp_path, auth_enabled=auth_enabled)
    client = TestClient(app)
    vid = client.post("/api/v1/vehicles", json=VEHICLE_PAYLOAD).json()["id"]
    return client, vid


# ─── Auth guard ───────────────────────────────────────────────────────────────


def test_commands_fail_closed_when_auth_not_configured(tmp_path: Path) -> None:
    """
    With Basic Auth disabled the commands are refused, not left open.

    This is the whole point of the guard: an unprotected deployment must not
    expose physical-world actions to anyone who can reach the port.
    """
    client, vid = _client_with_vehicle(tmp_path, auth_enabled=False)

    r = client.post(f"/api/v1/vehicles/{vid}/wake", auth=CREDS)

    assert r.status_code == 403
    assert "Basic Auth is not enabled" in r.json()["detail"]


def test_auth_enabled_without_password_hash_still_fails_closed(tmp_path: Path) -> None:
    """`enabled: true` with an empty hash must not authenticate anyone."""
    client, vid = _client_with_vehicle(tmp_path, auth_enabled=False)
    app_cfg = command_routes._app_config
    app_cfg.update_system(
        {"auth": {"enabled": True, "username": USERNAME, "passwordHash": ""}}
    )

    r = client.post(f"/api/v1/vehicles/{vid}/wake", auth=CREDS)

    assert r.status_code == 403


@pytest.mark.parametrize("path", ["wake", "charge-limit", "refresh"])
def test_every_command_requires_credentials(tmp_path: Path, path: str) -> None:
    """No command route is reachable without credentials."""
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(f"/api/v1/vehicles/{vid}/{path}", json={"percent": 80})

    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"].startswith("Basic")


@pytest.mark.parametrize(
    ("username", "password"),
    [
        (USERNAME, "wrong-password"),
        ("wrong-user", PASSWORD),
        ("wrong-user", "wrong-password"),
    ],
)
def test_bad_credentials_are_rejected(
    tmp_path: Path, username: str, password: str
) -> None:
    """A wrong username or password gets 401, never a partial pass."""
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(f"/api/v1/vehicles/{vid}/wake", auth=(username, password))

    assert r.status_code == 401


def test_auth_guard_returns_503_before_wiring(tmp_path: Path) -> None:
    """The guard reports 503 rather than failing open before init()."""
    app, _ = _make_app(tmp_path)
    security._app_config = None

    r = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/vehicles/anything/wake", auth=CREDS
    )
    assert r.status_code == 503


# ─── Guards ───────────────────────────────────────────────────────────────────


def test_command_returns_503_when_uninitialised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Commands return 503 before the router has been initialised."""
    app, _ = _make_app(tmp_path)
    monkeypatch.setattr(command_routes, "_app_config", None)

    r = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/vehicles/anything/wake", auth=CREDS
    )
    assert r.status_code == 503


def test_wake_unknown_vehicle_returns_404(tmp_path: Path) -> None:
    """Waking a vehicle that isn't configured returns 404."""
    app, _ = _make_app(tmp_path)

    r = TestClient(app).post("/api/v1/vehicles/no-such-id/wake", auth=CREDS)
    assert r.status_code == 404


@pytest.mark.parametrize("percent", [10, 49, 101, 200])
def test_charge_limit_rejects_out_of_range(tmp_path: Path, percent: int) -> None:
    """Charge-limit percentages outside 50-100 are rejected before any API call."""
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(
        f"/api/v1/vehicles/{vid}/charge-limit", json={"percent": percent}, auth=CREDS
    )
    assert r.status_code == 422


# ─── Commands ─────────────────────────────────────────────────────────────────


def test_wake_calls_tesla_and_returns_202(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /wake forwards to TeslaAPI.wake_up and reports the returned state."""
    calls: list[str] = []

    def _fake_wake(self: TeslaAPI) -> dict:
        calls.append(self.vehicle.teslaVehicleId)
        return {"state": "online"}

    monkeypatch.setattr(TeslaAPI, "wake_up", _fake_wake)
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(f"/api/v1/vehicles/{vid}/wake", auth=CREDS)

    assert r.status_code == 202
    assert r.json()["state"] == "online"
    assert calls == ["777"]


def test_charge_limit_calls_tesla_and_invalidates_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /charge-limit forwards the percent and drops the cached telemetry."""
    received: list[int] = []

    def _fake_set(self: TeslaAPI, percent: int) -> dict:  # noqa: ARG001
        received.append(percent)
        return {"response": {"result": True}}

    monkeypatch.setattr(TeslaAPI, "set_charge_limit", _fake_set)
    client, vid = _client_with_vehicle(tmp_path)
    vehicle = next(v for v in command_routes._app_config.vehicles if v.id == vid)
    telemetry_cache._cache[vid] = (0.0, telemetry_cache.base_status(vehicle))

    r = client.post(
        f"/api/v1/vehicles/{vid}/charge-limit", json={"percent": 80}, auth=CREDS
    )

    assert r.status_code == 200
    assert received == [80]
    assert telemetry_cache.age(vid) is None


class _FakeResponse:
    """Minimal stand-in for a requests.Response carrying a JSON body."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """Pass as a 200 — Tesla signals refusals in the body, not the status."""

    def json(self) -> dict:
        return self._payload


def _patch_tesla_post(monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    """Make every outbound Tesla command POST return *payload* with HTTP 200."""
    monkeypatch.setattr(
        "tesla_smart_charger.tesla_api.requests.post",
        lambda *args, **kwargs: _FakeResponse(payload),  # noqa: ARG005
    )


def test_charge_limit_surfaces_vehicle_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    A car that refuses the command must not be reported as success.

    Tesla answers a refusal with HTTP 200 and result=false — typically when the
    car is asleep — so the client has to inspect the body.
    """
    _patch_tesla_post(
        monkeypatch, {"response": {"result": False, "reason": "vehicle unavailable"}}
    )
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(
        f"/api/v1/vehicles/{vid}/charge-limit", json={"percent": 80}, auth=CREDS
    )

    assert r.status_code == 409
    assert "vehicle unavailable" in r.json()["detail"]


def test_charge_limit_accepts_a_successful_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """result=true passes through as a 200 — the rejection check isn't overeager."""
    _patch_tesla_post(monkeypatch, {"response": {"result": True, "reason": ""}})
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(
        f"/api/v1/vehicles/{vid}/charge-limit", json={"percent": 80}, auth=CREDS
    )

    assert r.status_code == 200
    assert r.json()["percent"] == 80


def test_refresh_evicts_cache_and_schedules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /refresh drops the cached entry and starts a background fetch."""
    started: list[str] = []
    monkeypatch.setattr(
        telemetry_cache,
        "schedule_refresh",
        lambda vehicle: bool(started.append(vehicle.id)) or True,
    )
    client, vid = _client_with_vehicle(tmp_path)
    vehicle = next(v for v in command_routes._app_config.vehicles if v.id == vid)
    telemetry_cache._cache[vid] = (0.0, telemetry_cache.base_status(vehicle))

    r = client.post(f"/api/v1/vehicles/{vid}/refresh", auth=CREDS)

    assert r.status_code == 202
    assert r.json()["refreshing"] is True
    assert started == [vid]
    assert telemetry_cache.age(vid) is None


# ─── Charge start/stop ─────────────────────────────────────────────────────────


def test_start_charge_calls_tesla_and_invalidates_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /charge/start forwards to start_charge and drops the cached telemetry."""
    received: list[str] = []

    def _fake_start(_self: TeslaAPI) -> dict:
        received.append("start")
        return {"response": {"result": True}}

    monkeypatch.setattr(TeslaAPI, "start_charge", _fake_start)
    client, vid = _client_with_vehicle(tmp_path)
    vehicle = next(v for v in command_routes._app_config.vehicles if v.id == vid)
    telemetry_cache._cache[vid] = (0.0, telemetry_cache.base_status(vehicle))

    r = client.post(f"/api/v1/vehicles/{vid}/charge/start", auth=CREDS)

    assert r.status_code == 200
    assert received == ["start"]
    assert telemetry_cache.age(vid) is None


def test_stop_charge_calls_tesla_and_invalidates_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /charge/stop forwards to stop_charge and drops the cached telemetry."""
    received: list[str] = []

    def _fake_stop(_self: TeslaAPI) -> dict:
        received.append("stop")
        return {"response": {"result": True}}

    monkeypatch.setattr(TeslaAPI, "stop_charge", _fake_stop)
    client, vid = _client_with_vehicle(tmp_path)
    vehicle = next(v for v in command_routes._app_config.vehicles if v.id == vid)
    telemetry_cache._cache[vid] = (0.0, telemetry_cache.base_status(vehicle))

    r = client.post(f"/api/v1/vehicles/{vid}/charge/stop", auth=CREDS)

    assert r.status_code == 200
    assert received == ["stop"]
    assert telemetry_cache.age(vid) is None


def test_start_charge_surfaces_vehicle_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A car that refuses the start charge command must not be reported as success."""
    _patch_tesla_post(
        monkeypatch, {"response": {"result": False, "reason": "vehicle unavailable"}}
    )
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(f"/api/v1/vehicles/{vid}/charge/start", auth=CREDS)

    assert r.status_code == 409
    assert "vehicle unavailable" in r.json()["detail"]


def test_stop_charge_surfaces_vehicle_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A car that refuses the stop charge command must not be reported as success."""
    _patch_tesla_post(
        monkeypatch, {"response": {"result": False, "reason": "vehicle unavailable"}}
    )
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(f"/api/v1/vehicles/{vid}/charge/stop", auth=CREDS)

    assert r.status_code == 409
    assert "vehicle unavailable" in r.json()["detail"]


@pytest.mark.parametrize("path", ["charge/start", "charge/stop"])
def test_charge_commands_require_credentials(tmp_path: Path, path: str) -> None:
    """Charge start/stop commands require credentials like other commands."""
    client, vid = _client_with_vehicle(tmp_path)

    r = client.post(f"/api/v1/vehicles/{vid}/{path}")

    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"].startswith("Basic")
