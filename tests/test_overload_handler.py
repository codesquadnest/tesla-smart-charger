"""Tests for the overload handler — updated for v2 multi-vehicle architecture."""

from unittest.mock import MagicMock, patch

import pytest

from tesla_smart_charger.handlers import overload_handler
from tesla_smart_charger.models import SystemConfig
from tesla_smart_charger.app_config import AppConfig


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_app_config(voltage: float = 230.0, home_max_amps: float = 32.0) -> AppConfig:
    """Return a minimal AppConfig with the given system settings."""
    cfg = AppConfig.__new__(AppConfig)
    cfg._system = SystemConfig(homeMaxAmps=home_max_amps, voltage=voltage)
    cfg._vehicles = []
    return cfg


# ─── _calculate_new_charge_limit ──────────────────────────────────────────────

@pytest.mark.parametrize(
    "current_charge_limit, current_em_consumption, max_charge_limit, min_charge_limit, house_max_power, expected",
    [
        (16, 16, 16, 6, 16, 16),
        (15, 17, 16, 6, 16, 14),
        (15, 18, 16, 6, 16, 13),
        (12, 15, 16, 6, 16, 13),
        (20, 27, 25, 6, 32, 25),
        (25, 35, 25, 6, 32, 22),
    ],
)
def test_calculate_new_charge_limit(
    current_charge_limit: float,
    current_em_consumption: float,
    max_charge_limit: float,
    min_charge_limit: float,
    house_max_power: float,
    expected: int,
) -> None:
    """Core algorithm: reduce by excess, clamp to [min, max]."""
    result = overload_handler._calculate_new_charge_limit(  # noqa: SLF001
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

    result = overload_handler._get_consumption(mock_em, app_config)  # noqa: SLF001
    assert result == pytest.approx(1.0)


def test_get_consumption_returns_zero_on_error() -> None:
    """ValueError from em controller → return 0.0."""
    app_config = _make_app_config(voltage=230.0)
    mock_em = MagicMock()
    mock_em.get_consumption.side_effect = ValueError("EM offline")

    result = overload_handler._get_consumption(mock_em, app_config)  # noqa: SLF001
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
            overload_handler._save_event("2024-01-01 12:00:00", "vehicle-uuid-123")  # noqa: SLF001

        mock_ctrl.insert_data.assert_called_once()
        call_kwargs = mock_ctrl.insert_data.call_args[0][0]
        assert call_kwargs["start"] == "2024-01-01 12:00:00"
        assert call_kwargs["end"] == "2024-01-01 12:01:30"
        assert call_kwargs["vehicle_id"] == "vehicle-uuid-123"
        mock_ctrl.close_connection.assert_called_once()


# ─── Session state ────────────────────────────────────────────────────────────

def test_session_flag_toggle() -> None:
    """is_session_active reflects _set_session calls."""
    overload_handler._set_session(False)  # noqa: SLF001
    assert overload_handler.is_session_active() is False

    overload_handler._set_session(True)  # noqa: SLF001
    assert overload_handler.is_session_active() is True

    overload_handler._set_session(False)  # noqa: SLF001
    assert overload_handler.is_session_active() is False

