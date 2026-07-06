"""Tests for AppConfig — loading, saving, migration, and vehicle CRUD."""

import json
import uuid
from pathlib import Path

import pytest

from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.models import OverloadStrategy, TeslaRegion, VehicleConfig


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """A temporary directory to use as the config directory."""
    return tmp_path / "config"


@pytest.fixture
def cfg(tmp_config_dir: Path) -> AppConfig:
    """A freshly loaded AppConfig backed by a temporary directory (no migration)."""
    app = AppConfig(str(tmp_config_dir))
    # Point legacy file to a path that never exists so migration is never triggered
    app._legacy_file = tmp_config_dir / "no_legacy_config.json"  # noqa: SLF001
    app.load()
    return app


# ─── Load / defaults ──────────────────────────────────────────────────────────


def test_load_creates_defaults_when_no_files(tmp_config_dir: Path) -> None:
    """First load with no existing files should produce sensible defaults."""
    app = AppConfig(str(tmp_config_dir))
    app._legacy_file = tmp_config_dir / "no_legacy.json"  # noqa: SLF001
    app.load()

    assert app.system.homeMaxAmps == 30.0
    assert app.system.voltage == 230.0
    assert app.system.region == TeslaRegion.EU
    assert app.system.configured is False
    assert app.vehicles == []


def test_load_reads_existing_system_json(tmp_config_dir: Path) -> None:
    """Existing system.json should be read and its values respected."""
    tmp_config_dir.mkdir(parents=True)
    system_data = {
        "homeMaxAmps": 40.0,
        "voltage": 120.0,
        "region": "na",
        "energyMonitorIp": "192.168.1.10",
        "energyMonitorType": "shelly_em",
        "sleepTimeSecs": 60,
        "downStepPercentage": 0.5,
        "upStepPercentage": 0.25,
        "overloadStrategy": "priority",
        "hostIp": "192.168.1.1",
        "apiPort": 9000,
        "auth": {"enabled": False, "username": "", "passwordHash": ""},
        "configured": True,
    }
    (tmp_config_dir / "system.json").write_text(json.dumps(system_data))
    (tmp_config_dir / "vehicles.json").write_text("[]")

    app = AppConfig(str(tmp_config_dir))
    app.load()

    assert app.system.homeMaxAmps == 40.0
    assert app.system.voltage == 120.0
    assert app.system.region == TeslaRegion.NA
    assert app.system.apiPort == 9000
    assert app.system.overloadStrategy == OverloadStrategy.PRIORITY
    assert app.system.configured is True


def test_load_reads_vehicles_json(tmp_config_dir: Path) -> None:
    """Existing vehicles.json should be loaded into the vehicles list."""
    tmp_config_dir.mkdir(parents=True)
    vid = str(uuid.uuid4())
    vehicles_data = [
        {
            "id": vid,
            "name": "Model Y",
            "vin": "5YJYGDEE1MF000001",
            "teslaVehicleId": "111",
            "teslaAccessToken": "tok_access",
            "teslaRefreshToken": "tok_refresh",
            "teslaHttpProxy": "http://localhost:4443",
            "teslaClientId": "client_abc",
            "chargerMaxAmps": 32.0,
            "chargerMinAmps": 6.0,
            "priority": 1,
            "enabled": True,
        }
    ]
    (tmp_config_dir / "system.json").write_text(json.dumps({"configured": False}))
    (tmp_config_dir / "vehicles.json").write_text(json.dumps(vehicles_data))

    app = AppConfig(str(tmp_config_dir))
    app.load()

    assert len(app.vehicles) == 1
    assert app.vehicles[0].id == vid
    assert app.vehicles[0].name == "Model Y"
    assert app.vehicles[0].chargerMaxAmps == 32.0


def test_system_property_raises_before_load(tmp_config_dir: Path) -> None:
    """Accessing .system before load() should raise RuntimeError."""
    app = AppConfig(str(tmp_config_dir))
    with pytest.raises(RuntimeError, match="not loaded"):
        _ = app.system


# ─── Migration ────────────────────────────────────────────────────────────────


def test_migration_from_legacy_config(tmp_path: Path) -> None:
    """Legacy config.json should be migrated to system.json + vehicles.json."""
    legacy = tmp_path / "config.json"
    legacy.write_text(
        json.dumps(
            {
                "homeMaxAmps": 25.0,
                "chargerMaxAmps": 20.0,
                "chargerMinAmps": 6.0,
                "downStepPercentage": 0.5,
                "upStepPercentage": 0.25,
                "sleepTimeSecs": 30,
                "energyMonitorIp": "10.0.0.1",
                "energyMonitorType": "shelly_em",
                "hostIp": "10.0.0.2",
                "apiPort": 8000,
                "teslaVehicleId": "99999",
                "teslaAccessToken": "at_legacy",
                "teslaRefreshToken": "rt_legacy",
                "teslaHttpProxy": "http://proxy:4443",
                "teslaClientId": "cid_legacy",
            }
        )
    )

    config_dir = tmp_path / "config"
    # Patch _legacy_file to point to tmp_path/config.json
    app = AppConfig(str(config_dir))
    app._legacy_file = legacy  # noqa: SLF001

    app.load()

    assert app.system.homeMaxAmps == 25.0
    assert app.system.energyMonitorIp == "10.0.0.1"
    assert app.system.configured is True
    assert len(app.vehicles) == 1
    v = app.vehicles[0]
    assert v.teslaAccessToken == "at_legacy"
    assert v.chargerMaxAmps == 20.0
    assert v.teslaVehicleId == "99999"

    # system.json and vehicles.json should now exist
    assert (config_dir / "system.json").exists()
    assert (config_dir / "vehicles.json").exists()


def test_migration_skipped_when_system_json_exists(tmp_path: Path) -> None:
    """Migration should NOT run if system.json already exists alongside config.json."""
    legacy = tmp_path / "config.json"
    legacy.write_text(json.dumps({"homeMaxAmps": 99.0}))

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    # Write a valid system.json — migration should be skipped
    (config_dir / "system.json").write_text(json.dumps({"homeMaxAmps": 10.0, "configured": True}))
    (config_dir / "vehicles.json").write_text("[]")

    app = AppConfig(str(config_dir))
    app._legacy_file = legacy  # noqa: SLF001
    app.load()

    # system.json's value wins (migration was skipped)
    assert app.system.homeMaxAmps == 10.0


# ─── Save / persist ───────────────────────────────────────────────────────────


def test_save_system_round_trips(cfg: AppConfig, tmp_config_dir: Path) -> None:
    """save_system should write JSON that can be re-read correctly."""
    cfg.update_system({"homeMaxAmps": 50.0, "voltage": 110.0})

    app2 = AppConfig(str(tmp_config_dir))
    app2.load()

    assert app2.system.homeMaxAmps == 50.0
    assert app2.system.voltage == 110.0


# ─── Vehicle CRUD ─────────────────────────────────────────────────────────────


def test_add_vehicle(cfg: AppConfig) -> None:
    """add_vehicle should append and persist the new vehicle."""
    v = VehicleConfig(name="Model 3", teslaAccessToken="tok1")
    result = cfg.add_vehicle(v)

    assert result.name == "Model 3"
    assert len(cfg.vehicles) == 1
    assert cfg.vehicles[0].id == result.id


def test_get_vehicle_found(cfg: AppConfig) -> None:
    v = cfg.add_vehicle(VehicleConfig(name="Model S"))
    found = cfg.get_vehicle(v.id)
    assert found is not None
    assert found.name == "Model S"


def test_get_vehicle_not_found(cfg: AppConfig) -> None:
    assert cfg.get_vehicle("nonexistent-id") is None


def test_update_vehicle(cfg: AppConfig) -> None:
    v = cfg.add_vehicle(VehicleConfig(name="Roadster", chargerMaxAmps=16.0))
    updated = cfg.update_vehicle(v.id, {"chargerMaxAmps": 32.0, "name": "Roadster 2"})

    assert updated is not None
    assert updated.chargerMaxAmps == 32.0
    assert updated.name == "Roadster 2"
    # In-memory state updated
    assert cfg.vehicles[0].chargerMaxAmps == 32.0


def test_update_vehicle_returns_none_for_unknown_id(cfg: AppConfig) -> None:
    result = cfg.update_vehicle("no-such-id", {"name": "Ghost"})
    assert result is None


def test_remove_vehicle(cfg: AppConfig) -> None:
    v = cfg.add_vehicle(VehicleConfig(name="Cybertruck"))
    assert cfg.remove_vehicle(v.id) is True
    assert cfg.vehicles == []


def test_remove_vehicle_returns_false_for_unknown_id(cfg: AppConfig) -> None:
    assert cfg.remove_vehicle("ghost-id") is False


def test_update_vehicle_tokens(cfg: AppConfig) -> None:
    v = cfg.add_vehicle(VehicleConfig(teslaAccessToken="old_at", teslaRefreshToken="old_rt"))
    cfg.update_vehicle_tokens(v.id, "new_at", "new_rt")
    updated = cfg.get_vehicle(v.id)
    assert updated is not None
    assert updated.teslaAccessToken == "new_at"
    assert updated.teslaRefreshToken == "new_rt"


def test_multiple_vehicles(cfg: AppConfig) -> None:
    cfg.add_vehicle(VehicleConfig(name="Car A", priority=1))
    cfg.add_vehicle(VehicleConfig(name="Car B", priority=2))
    cfg.add_vehicle(VehicleConfig(name="Car C", priority=3))

    assert len(cfg.vehicles) == 3
    names = [v.name for v in cfg.vehicles]
    assert "Car A" in names and "Car C" in names


# ─── update_system ────────────────────────────────────────────────────────────


def test_update_system_merges_fields(cfg: AppConfig) -> None:
    original_voltage = cfg.system.voltage
    cfg.update_system({"homeMaxAmps": 99.0})

    assert cfg.system.homeMaxAmps == 99.0
    assert cfg.system.voltage == original_voltage  # unchanged


def test_update_system_nested_auth(cfg: AppConfig) -> None:
    cfg.update_system({"auth": {"enabled": True, "username": "admin", "passwordHash": "hash123"}})

    assert cfg.system.auth.enabled is True
    assert cfg.system.auth.username == "admin"
    assert cfg.system.auth.passwordHash == "hash123"


def test_mark_configured(cfg: AppConfig) -> None:
    assert cfg.system.configured is False
    cfg.mark_configured()
    assert cfg.system.configured is True
    assert cfg.is_configured is True
