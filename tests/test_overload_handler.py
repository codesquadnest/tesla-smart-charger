"""Tests for the overload handler — updated for v2 multi-vehicle architecture."""

from unittest.mock import MagicMock, patch

import pytest

from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.handlers import overload_handler
from tesla_smart_charger.models import SystemConfig, VehicleConfig

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_app_config(voltage: float = 230.0, home_max_amps: float = 32.0) -> AppConfig:
    """Return a minimal AppConfig with the given system settings."""
    cfg = AppConfig.__new__(AppConfig)
    cfg._system = SystemConfig(homeMaxAmps=home_max_amps, voltage=voltage)
    cfg._vehicles = []
    return cfg


def _make_vehicle(**overrides: object) -> VehicleConfig:
    """Return a minimal VehicleConfig with sensible charger limits."""
    defaults: dict[str, object] = {
        "id": "vehicle-1",
        "teslaVehicleId": "12345",
        "chargerMaxAmps": 25.0,
        "chargerMinAmps": 6.0,
    }
    defaults.update(overrides)
    return VehicleConfig(**defaults)


# ─── _calculate_new_charge_limit ──────────────────────────────────────────────


@pytest.mark.parametrize(
    (
        "current_charge_limit",
        "current_em_consumption",
        "max_charge_limit",
        "min_charge_limit",
        "house_max_power",
        "expected",
    ),
    [
        (16, 16, 16, 6, 16, 16),
        (15, 17, 16, 6, 16, 14),
        (15, 18, 16, 6, 16, 13),
        (12, 15, 16, 6, 16, 13),
        (20, 27, 25, 6, 32, 25),
        (25, 35, 25, 6, 32, 22),
    ],
)
def test_calculate_new_charge_limit(  # noqa: PLR0913, PLR0917
    current_charge_limit: float,
    current_em_consumption: float,
    max_charge_limit: float,
    min_charge_limit: float,
    house_max_power: float,
    expected: int,
) -> None:
    """Core algorithm: reduce by excess, clamp to [min, max]."""
    result = overload_handler._calculate_new_charge_limit(
        current_charge_limit,
        current_em_consumption,
        max_charge_limit,
        min_charge_limit,
        house_max_power,
    )
    assert result == expected


# ─── _get_consumption ─────────────────────────────────────────────────────────


def test_get_consumption_returns_amps() -> None:
    """230 W / 230 V = 1.0 A."""
    app_config = _make_app_config(voltage=230.0)
    mock_em = MagicMock()
    mock_em.get_consumption.return_value = 230.0

    result = overload_handler._get_consumption(mock_em, app_config)
    assert result == pytest.approx(1.0)


def test_get_consumption_returns_zero_on_error() -> None:
    """ValueError from em controller → return 0.0."""
    app_config = _make_app_config(voltage=230.0)
    mock_em = MagicMock()
    mock_em.get_consumption.side_effect = ValueError("EM offline")

    result = overload_handler._get_consumption(mock_em, app_config)
    assert result == 0.0


# ─── _save_event ──────────────────────────────────────────────────────────────


def test_save_event_calls_insert_data() -> None:
    """_save_event should call insert_data on the DB controller."""
    with patch(
        "tesla_smart_charger.handlers.overload_handler.db_controller.create_database_controller"
    ) as mock_factory:
        mock_ctrl = MagicMock()
        mock_factory.return_value = mock_ctrl

        with patch("time.strftime") as mock_strftime:
            mock_strftime.return_value = "2024-01-01 12:01:30"
            overload_handler._save_event("2024-01-01 12:00:00", "vehicle-uuid-123")

        mock_ctrl.insert_data.assert_called_once()
        call_kwargs = mock_ctrl.insert_data.call_args[0][0]
        assert call_kwargs["start"] == "2024-01-01 12:00:00"
        assert call_kwargs["end"] == "2024-01-01 12:01:30"
        assert call_kwargs["vehicle_id"] == "vehicle-uuid-123"
        mock_ctrl.close_connection.assert_called_once()


# ─── Session state ────────────────────────────────────────────────────────────


def test_session_flag_toggle() -> None:
    """is_session_active reflects _set_session calls."""
    overload_handler._set_session(active=False)
    assert overload_handler.is_session_active() is False

    overload_handler._set_session(active=True)
    assert overload_handler.is_session_active() is True

    overload_handler._set_session(active=False)
    assert overload_handler.is_session_active() is False


# ─── _intended_amp_limit ──────────────────────────────────────────────────────


def test_intended_amp_limit_prefers_current_request() -> None:
    """User's requested limit is read from charge_current_request first."""
    vehicle = _make_vehicle()
    data = {"charge_state": {"charge_amps": 20, "charge_current_request": 22}}

    assert overload_handler._intended_amp_limit(data, vehicle) == 22


def test_intended_amp_limit_falls_back_to_charge_amps() -> None:
    """charge_amps is used as a compatibility fallback when the setpoint is absent."""
    vehicle = _make_vehicle()
    data = {"charge_state": {"charge_amps": 20}}

    assert overload_handler._intended_amp_limit(data, vehicle) == 20


def test_intended_amp_limit_falls_back_to_current_request() -> None:
    """charge_current_request is used when charge_amps is missing."""
    vehicle = _make_vehicle()
    data = {"charge_state": {"charge_current_request": 22}}

    assert overload_handler._intended_amp_limit(data, vehicle) == 22


def test_intended_amp_limit_falls_back_to_configured_max() -> None:
    """Configured max is used when the car reports no requested limit."""
    vehicle = _make_vehicle(chargerMaxAmps=32.0)
    data = {"charge_state": {}}

    assert overload_handler._intended_amp_limit(data, vehicle) == 32


# ─── _ramp_up_ceiling ─────────────────────────────────────────────────────────


def test_ramp_up_ceiling_capped_by_intended_limit() -> None:
    """Ramp-up ceiling never exceeds the user's requested limit."""
    vehicle = _make_vehicle(chargerMaxAmps=25.0)

    assert overload_handler._ramp_up_ceiling(vehicle, {vehicle.id: 20}) == 20


def test_ramp_up_ceiling_capped_by_configured_max() -> None:
    """Configured max wins even if the user requested more than it."""
    vehicle = _make_vehicle(chargerMaxAmps=25.0)

    assert overload_handler._ramp_up_ceiling(vehicle, {vehicle.id: 32}) == 25


def test_ramp_up_ceiling_defaults_to_configured_max() -> None:
    """Configured max is the default when nothing was captured for a vehicle."""
    vehicle = _make_vehicle(chargerMaxAmps=25.0)

    assert overload_handler._ramp_up_ceiling(vehicle, {}) == 25


# ─── _apply_ramp_up ───────────────────────────────────────────────────────────


def test_ramp_up_caps_set_limit_at_intended() -> None:
    """Ramp-up sets the user's intended limit, not the configured max."""
    vehicle = _make_vehicle()

    api = MagicMock()
    charging = [(vehicle, api, {"charge_state": {"charger_actual_current": 18.0}})]
    state = overload_handler._AdjustmentState(intended_amperage={vehicle.id: 20.0})

    with patch(
        "tesla_smart_charger.handlers.overload_handler.time.time", return_value=1000.0
    ):
        result = overload_handler._apply_ramp_up(
            charging, em_amps=25.0, cfg=SystemConfig(), state=state
        )

    # step = 0.25 * (25-6) = 4.75 → 18 + 4.75 caps at 20, not 22+
    api.set_charge_amp_limit.assert_called_once_with(20)
    assert result is False


def test_ramp_up_invalidates_telemetry_cache() -> None:
    """A successful ramp-up drops cached telemetry so the UI refreshes."""
    vehicle = _make_vehicle()
    api = MagicMock()
    charging = [(vehicle, api, {"charge_state": {"charger_actual_current": 18.0}})]
    state = overload_handler._AdjustmentState(intended_amperage={vehicle.id: 20.0})

    with patch(
        "tesla_smart_charger.handlers.overload_handler.time.time", return_value=1000.0
    ), patch(
        "tesla_smart_charger.handlers.overload_handler.telemetry_cache.invalidate"
    ) as mock_invalidate:
        overload_handler._apply_ramp_up(
            charging, em_amps=25.0, cfg=SystemConfig(), state=state
        )

    mock_invalidate.assert_called_once_with(vehicle.id)
