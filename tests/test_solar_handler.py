"""Tests for the solar surplus handler."""

from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.handlers import overload_handler, solar_handler
from tesla_smart_charger.models import SystemConfig, VehicleConfig

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_app_config(
    voltage: float = 230.0,
    home_max_amps: float = 32.0,
    solar_target: float = 1.0,
    *,
    solar_enabled: bool = True,
) -> AppConfig:
    """Return a minimal AppConfig with the given system settings."""
    cfg = AppConfig.__new__(AppConfig)
    cfg._system = SystemConfig(
        homeMaxAmps=home_max_amps,
        voltage=voltage,
        solarSurplusEnabled=solar_enabled,
        solarTargetAmps=solar_target,
        energyMonitorType="shelly_em",
        energyMonitorIp="192.168.1.10",
    )
    cfg._vehicles = []
    return cfg


def _make_vehicle(
    name: str = "Model Y",
    max_amps: float = 25.0,
    min_amps: float = 6.0,
    priority: int = 1,
) -> VehicleConfig:
    return VehicleConfig(
        id=f"uid-{name}",
        name=name,
        vin="5YJYGDEE1MF000001",
        teslaVehicleId="777",
        chargerMaxAmps=max_amps,
        chargerMinAmps=min_amps,
        priority=priority,
        enabled=True,
    )


def _make_charging(vehicle: VehicleConfig, current: float) -> list:
    """Return a single charging (vehicle, api, data) tuple."""
    api = MagicMock()
    data = {
        "state": "online",
        "charge_state": {
            "charging_state": "Charging",
            "charger_actual_current": current,
        },
    }
    return [(vehicle, api, data)]


# ─── _apply_solar_adjustment ──────────────────────────────────────────────────


def test_adjustment_exports_raise_charge_amp() -> None:
    """Exporting (negative em) increases the charge limit."""
    app_config = _make_app_config()
    vehicle = _make_vehicle()
    charging = _make_charging(vehicle, current=10.0)

    changed = solar_handler._apply_solar_adjustment(charging, -5.0, app_config.system)

    assert changed is True
    charging[0][1].set_charge_amp_limit.assert_called_once()
    new_limit = charging[0][1].set_charge_amp_limit.call_args[0][0]
    assert new_limit == 16  # 10 + (1 - (-5)) = 16


def test_adjustment_import_reduces_charge_amp() -> None:
    """Importing (positive em above target) reduces the charge limit."""
    app_config = _make_app_config()
    vehicle = _make_vehicle()
    charging = _make_charging(vehicle, current=10.0)

    changed = solar_handler._apply_solar_adjustment(charging, 7.0, app_config.system)

    assert changed is True
    # delta = 1 - 7 = -6 → new = 10 - 6 = 4, clamped to min 6.
    new_limit = charging[0][1].set_charge_amp_limit.call_args[0][0]
    assert new_limit == 6


def test_adjustment_clamps_to_minimum() -> None:
    """Reduction never goes below the vehicle's minimum amps."""
    app_config = _make_app_config(solar_target=0.0)
    vehicle = _make_vehicle(min_amps=6.0)
    charging = _make_charging(vehicle, current=8.0)

    changed = solar_handler._apply_solar_adjustment(charging, 10.0, app_config.system)

    assert changed is True
    new_limit = charging[0][1].set_charge_amp_limit.call_args[0][0]
    assert new_limit == 6


def test_adjustment_no_change_when_balanced() -> None:
    """A grid already at target issues no command."""
    app_config = _make_app_config(solar_target=1.0)
    vehicle = _make_vehicle()
    charging = _make_charging(vehicle, current=10.0)

    changed = solar_handler._apply_solar_adjustment(charging, 1.1, app_config.system)

    assert changed is False
    charging[0][1].set_charge_amp_limit.assert_not_called()


def test_adjustment_handles_multiple_vehicles() -> None:
    """The surplus/import delta is split proportionally across vehicles."""
    app_config = _make_app_config()
    v1 = _make_vehicle("A", max_amps=20.0, min_amps=6.0)
    v2 = _make_vehicle("B", max_amps=30.0, min_amps=6.0)
    api1, api2 = MagicMock(), MagicMock()
    charging = [
        (
            v1,
            api1,
            {
                "state": "online",
                "charge_state": {
                    "charging_state": "Charging",
                    "charger_actual_current": 10.0,
                },
            },
        ),
        (
            v2,
            api2,
            {
                "state": "online",
                "charge_state": {
                    "charging_state": "Charging",
                    "charger_actual_current": 20.0,
                },
            },
        ),
    ]

    changed = solar_handler._apply_solar_adjustment(charging, -9.0, app_config.system)

    # total current = 30; delta = 1 - (-9) = 10
    # v1 share: 10/30 * 10 = +3.33 → 13; v2 share: 20/30 * 10 = +6.67 → 26
    assert changed is True
    assert api1.set_charge_amp_limit.call_args[0][0] == 13
    assert api2.set_charge_amp_limit.call_args[0][0] == 26


# ─── trigger_solar guards ─────────────────────────────────────────────────────


def test_trigger_solar_refuses_when_already_active() -> None:
    """A running solar session refuses a second trigger."""
    app_config = _make_app_config()
    solar_handler._set_session(active=True)
    try:
        ok, msg = solar_handler.trigger_solar(app_config)
        assert ok is False
        assert "already active" in msg
    finally:
        solar_handler._set_session(active=False)


def test_trigger_solar_refuses_when_overload_active() -> None:
    """Solar refuses to start while the overload handler holds the cars."""
    app_config = _make_app_config()
    overload_handler._set_session(active=True)
    try:
        ok, msg = solar_handler.trigger_solar(app_config)
        assert ok is False
        assert "overload" in msg
    finally:
        overload_handler._set_session(active=False)


def test_trigger_solar_refuses_when_disabled() -> None:
    """Solar refuses when solar surplus mode is turned off."""
    app_config = _make_app_config(solar_enabled=False)
    ok, msg = solar_handler.trigger_solar(app_config)
    assert ok is False
    assert "not enabled" in msg


def test_trigger_solar_refuses_without_vehicles() -> None:
    """Solar refuses when no vehicles are configured."""
    app_config = _make_app_config()
    ok, msg = solar_handler.trigger_solar(app_config)
    assert ok is False
    assert "no vehicles configured" in msg


def test_trigger_solar_refuses_when_nothing_charging() -> None:
    """Solar refuses when no configured vehicle is currently charging."""
    app_config = _make_app_config()
    app_config._vehicles = [_make_vehicle()]
    data = {"state": "online", "charge_state": {}}
    with patch("tesla_smart_charger.handlers.solar_handler.TeslaAPI") as mock_api_cls:
        mock_api = mock_api_cls.return_value
        mock_api.get_vehicle_data.return_value = data
        ok, msg = solar_handler.trigger_solar(app_config)
        assert ok is False
        assert "no vehicles are currently charging" in msg


def test_trigger_solar_starts_session() -> None:
    """A charging vehicle and surplus lets trigger_solar start a session."""
    app_config = _make_app_config()
    app_config._vehicles = [_make_vehicle()]
    data = {
        "state": "online",
        "charge_state": {"charging_state": "Charging", "charger_actual_current": 10.0},
    }
    with (
        patch("tesla_smart_charger.handlers.solar_handler.TeslaAPI") as mock_api_cls,
        patch("tesla_smart_charger.handlers.solar_handler.handle_solar"),
    ):
        mock_api_cls.return_value.get_vehicle_data.return_value = data
        ok, msg = solar_handler.trigger_solar(app_config)
        assert ok is True
        assert "started" in msg


def test_trigger_solar_propagates_http_error_as_skip() -> None:
    """A Tesla API error during the charging check aborts the trigger."""
    app_config = _make_app_config()
    app_config._vehicles = [_make_vehicle()]
    with patch("tesla_smart_charger.handlers.solar_handler.TeslaAPI") as mock_api_cls:
        mock_api = mock_api_cls.return_value
        mock_api.get_vehicle_data.side_effect = HTTPException(status_code=408)
        ok, _msg = solar_handler.trigger_solar(app_config)
        assert ok is False


# ─── handle_solar lifecycle ───────────────────────────────────────────────────


def test_handle_solar_ends_and_clears_flag_on_error() -> None:
    """A ValueError while building the EM controller clears the session flag."""
    app_config = _make_app_config()
    with (
        patch(
            "tesla_smart_charger.handlers.solar_handler._em_controller.create_energy_monitor_controller",
            side_effect=ValueError("bad em"),
        ),
        patch(
            "tesla_smart_charger.handlers.solar_handler._set_session",
            wraps=solar_handler._set_session,
        ),
    ):
        solar_handler.handle_solar(app_config)

    assert solar_handler.is_surplus_active() is False


def test_handle_solar_yields_when_disabled() -> None:
    """A session exits immediately when solar mode is disabled."""
    app_config = _make_app_config(solar_enabled=False)
    with (
        patch(
            "tesla_smart_charger.handlers.solar_handler._em_controller.create_energy_monitor_controller"
        ) as mock_factory,
        patch(
            "tesla_smart_charger.handlers.solar_handler._set_session",
            wraps=solar_handler._set_session,
        ),
    ):
        mock_factory.return_value = MagicMock()
        solar_handler.handle_solar(app_config)
    assert solar_handler.is_surplus_active() is False


def test_handle_solar_runs_adjustment_loop_until_no_change() -> None:
    """The loop ends after stable reads when nothing needs adjusting."""
    app_config = _make_app_config()
    app_config._vehicles = [_make_vehicle()]
    data = {
        "state": "online",
        "charge_state": {"charging_state": "Charging", "charger_actual_current": 10.0},
    }
    with (
        patch("tesla_smart_charger.handlers.solar_handler.TeslaAPI") as mock_api_cls,
        patch(
            "tesla_smart_charger.handlers.solar_handler._em_controller.create_energy_monitor_controller"
        ) as mock_factory,
        patch("tesla_smart_charger.handlers.solar_handler.time.sleep"),
        patch(
            "tesla_smart_charger.handlers.solar_handler.time.time", return_value=100.0
        ),
    ):
        mock_api_cls.return_value.get_vehicle_data.return_value = data
        mock_em = mock_factory.return_value
        # Grid at exactly the target (1.0A) — nothing changes, loop ends after
        # _STABLE_NEEDED no-change reads.
        mock_em.get_consumption.return_value = 230.0  # 230W / 230V = 1.0A

        solar_handler.handle_solar(app_config)

    assert solar_handler.is_surplus_active() is False
