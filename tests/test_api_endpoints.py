"""
Integration-level tests for FastAPI endpoints.

Each test creates its own isolated AppConfig backed by a temporary directory,
injects it directly into the route modules (bypassing __main__.py startup), and
uses FastAPI's TestClient for HTTP calls.  No real Tesla API or DB calls are made.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.routes import (
    auth_routes,
    config_routes,
    history_routes,
    status_routes,
    vehicle_routes,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_app(tmp_path: Path) -> tuple[FastAPI, AppConfig]:
    """Build a minimal FastAPI app wired to a fresh AppConfig in tmp_path."""
    app_cfg = AppConfig(str(tmp_path / "config"))
    # Prevent migration from picking up the project-root config.json
    app_cfg._legacy_file = tmp_path / "no_legacy.json"  # noqa: SLF001
    app_cfg.load()

    app = FastAPI()

    config_routes.init(app_cfg)
    vehicle_routes.init(app_cfg)
    auth_routes.init(app_cfg)
    status_routes.init(
        app_cfg,
        monitor_active_fn=lambda: False,
        overload_active_fn=lambda: False,
    )

    app.include_router(status_routes.router)
    app.include_router(config_routes.router)
    app.include_router(vehicle_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(history_routes.router)

    return app, app_cfg


# ─── GET /api/v1/status ───────────────────────────────────────────────────────


def test_status_returns_200(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app, raise_server_exceptions=True)

    r = client.get("/api/v1/status")
    assert r.status_code == 200
    body = r.json()
    assert "configured" in body
    assert "homeMaxAmps" in body
    assert "vehicles" in body
    assert isinstance(body["vehicles"], list)


def test_status_configured_false_by_default(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.get("/api/v1/status")
    assert r.json()["configured"] is False


def test_status_monitor_and_overload_flags(tmp_path: Path) -> None:
    app_cfg = AppConfig(str(tmp_path / "config"))
    app_cfg._legacy_file = tmp_path / "no_legacy.json"  # noqa: SLF001
    app_cfg.load()

    app = FastAPI()
    status_routes.init(app_cfg, monitor_active_fn=lambda: True, overload_active_fn=lambda: True)
    app.include_router(status_routes.router)

    client = TestClient(app)
    body = client.get("/api/v1/status").json()
    assert body["monitorActive"] is True
    assert body["overloadActive"] is True


# ─── GET /api/v1/config ───────────────────────────────────────────────────────


def test_get_config_returns_200(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert "homeMaxAmps" in body
    assert "voltage" in body
    # Password hash must NOT be in the response
    auth = body.get("auth", {})
    assert "passwordHash" not in auth


def test_post_config_updates_field(tmp_path: Path) -> None:
    app, app_cfg = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post("/api/v1/config", json={"homeMaxAmps": 55.0})
    assert r.status_code == 200
    assert r.json()["homeMaxAmps"] == 55.0
    # Persisted
    assert app_cfg.system.homeMaxAmps == 55.0


def test_post_config_empty_body_returns_400(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post("/api/v1/config", json={})
    assert r.status_code == 400


def test_post_config_invalid_field_ignored(tmp_path: Path) -> None:
    """Unknown fields are ignored (Pydantic strips them)."""
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    # Only send an unknown key — should be treated as empty update
    r = client.post("/api/v1/config", json={"nonexistentField": "foo"})
    assert r.status_code == 400


# ─── Vehicle CRUD ─────────────────────────────────────────────────────────────


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


def test_list_vehicles_empty(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.get("/api/v1/vehicles")
    assert r.status_code == 200
    assert r.json() == []


def test_add_vehicle_returns_201(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post("/api/v1/vehicles", json=VEHICLE_PAYLOAD)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Model Y"
    # Tokens should be redacted in the response
    assert body["teslaAccessToken"] == "***"
    assert body["teslaRefreshToken"] == "***"
    assert "id" in body


def test_get_vehicle_by_id(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    vid = client.post("/api/v1/vehicles", json=VEHICLE_PAYLOAD).json()["id"]
    r = client.get(f"/api/v1/vehicles/{vid}")
    assert r.status_code == 200
    assert r.json()["id"] == vid


def test_get_vehicle_not_found_returns_404(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.get("/api/v1/vehicles/no-such-id")
    assert r.status_code == 404


def test_patch_vehicle(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    vid = client.post("/api/v1/vehicles", json=VEHICLE_PAYLOAD).json()["id"]
    r = client.patch(f"/api/v1/vehicles/{vid}", json={"chargerMaxAmps": 16.0})
    assert r.status_code == 200
    assert r.json()["chargerMaxAmps"] == 16.0


def test_patch_vehicle_empty_body_returns_400(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    vid = client.post("/api/v1/vehicles", json=VEHICLE_PAYLOAD).json()["id"]
    r = client.patch(f"/api/v1/vehicles/{vid}", json={})
    assert r.status_code == 400


def test_delete_vehicle(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    vid = client.post("/api/v1/vehicles", json=VEHICLE_PAYLOAD).json()["id"]
    r = client.delete(f"/api/v1/vehicles/{vid}")
    assert r.status_code == 200

    r2 = client.get(f"/api/v1/vehicles/{vid}")
    assert r2.status_code == 404


def test_delete_vehicle_not_found_returns_404(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.delete("/api/v1/vehicles/no-such-id")
    assert r.status_code == 404


def test_vehicles_persist_across_reload(tmp_path: Path) -> None:
    """Vehicles written via POST should survive a fresh AppConfig load."""
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    client.post("/api/v1/vehicles", json=VEHICLE_PAYLOAD)

    app2_cfg = AppConfig(str(tmp_path / "config"))
    app2_cfg._legacy_file = tmp_path / "no_legacy.json"  # noqa: SLF001
    app2_cfg.load()
    assert len(app2_cfg.vehicles) == 1
    assert app2_cfg.vehicles[0].name == "Model Y"


# ─── Auth setup / verify ──────────────────────────────────────────────────────


def test_auth_setup_enable(tmp_path: Path) -> None:
    app, app_cfg = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post(
        "/api/v1/auth/setup",
        json={"enabled": True, "username": "admin", "password": "secret"},
    )
    assert r.status_code == 200
    assert app_cfg.system.auth.enabled is True
    assert app_cfg.system.auth.username == "admin"
    assert app_cfg.system.auth.passwordHash != ""


def test_auth_setup_enable_missing_password_returns_400(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post("/api/v1/auth/setup", json={"enabled": True, "username": "admin"})
    assert r.status_code == 400


def test_auth_verify_no_auth_always_valid(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post("/api/v1/auth/verify?username=anyone", json={"password": "whatever"})
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_auth_verify_correct_credentials(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    client.post(
        "/api/v1/auth/setup",
        json={"enabled": True, "username": "admin", "password": "correctpassword"},
    )
    r = client.post("/api/v1/auth/verify?username=admin", json={"password": "correctpassword"})
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_auth_verify_wrong_password_returns_401(tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    client.post(
        "/api/v1/auth/setup",
        json={"enabled": True, "username": "admin", "password": "correctpassword"},
    )
    r = client.post("/api/v1/auth/verify?username=admin", json={"password": "wrongpassword"})
    assert r.status_code == 401


def test_auth_disable(tmp_path: Path) -> None:
    app, app_cfg = _make_app(tmp_path)
    client = TestClient(app)

    # Enable first, then disable
    client.post(
        "/api/v1/auth/setup",
        json={"enabled": True, "username": "admin", "password": "s3cr3t"},
    )
    client.post("/api/v1/auth/setup", json={"enabled": False})
    assert app_cfg.system.auth.enabled is False


# ─── GET /api/v1/history ──────────────────────────────────────────────────────


def test_history_returns_200_with_in_memory_db(tmp_path: Path) -> None:
    """History endpoint should succeed even with an in-memory/new SQLite DB."""
    from tesla_smart_charger import constants

    db_path = str(tmp_path / "test.db")
    original_db_type = constants.DB_TYPE
    original_db_path = constants.DB_FILE_PATH

    constants.DB_TYPE = "sqlite"
    constants.DB_FILE_PATH = db_path

    try:
        app, _ = _make_app(tmp_path)
        client = TestClient(app)

        r = client.get("/api/v1/history")
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert "count" in body
        assert body["data"] == []
    finally:
        constants.DB_TYPE = original_db_type
        constants.DB_FILE_PATH = original_db_path


# ─── OAuth callback HTML ─────────────────────────────────────────────────────


def test_auth_callback_invalid_state_returns_html_error(tmp_path: Path) -> None:
    """Bad state should return 200 HTML page with error payload (not a JSON 400)."""
    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    r = client.get("/auth/callback?code=abc&state=invalid_state")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "tesla-auth-callback" in r.text
    assert "Invalid or expired" in r.text
