"""Tests for the energy monitor cron's solar integration."""

from unittest.mock import MagicMock, patch

import pytest

from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.cron import em_cron
from tesla_smart_charger.handlers import solar_handler
from tesla_smart_charger.models import SystemConfig

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_app_config(**system_kwargs: object) -> AppConfig:
    defaults: dict[str, object] = {
        "homeMaxAmps": 32.0,
        "voltage": 230.0,
        "solarSurplusEnabled": True,
        "solarTargetAmps": 1.0,
        "energyMonitorIp": "192.168.1.10",
        "energyMonitorType": "shelly_em",
    }
    defaults.update(system_kwargs)
    cfg = AppConfig.__new__(AppConfig)
    cfg._system = SystemConfig(**defaults)
    cfg._vehicles = []
    return cfg


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    """Reset module globals between tests."""
    em_cron.OVERLOAD = False
    em_cron.LAST_CONSUMPTION_AMPS = None
    em_cron.LAST_SURPLUS_AMPS = None
    em_cron._last_solar_attempt = 0.0
    solar_handler._set_session(active=False)
    yield
    em_cron.OVERLOAD = False
    em_cron.LAST_CONSUMPTION_AMPS = None
    em_cron.LAST_SURPLUS_AMPS = None
    em_cron._last_solar_attempt = 0.0
    solar_handler._set_session(active=False)


# ─── _check_power_consumption ─────────────────────────────────────────────────


def test_tracks_surplus_on_export() -> None:
    """A negative grid reading is recorded as surplus amps."""
    app_config = _make_app_config()
    em_ctrl = MagicMock()
    em_ctrl.get_consumption.return_value = -1150.0  # export 1150W

    em_cron._check_power_consumption(em_ctrl, app_config)

    assert pytest.approx(-5.0) == em_cron.LAST_CONSUMPTION_AMPS
    assert pytest.approx(5.0) == em_cron.LAST_SURPLUS_AMPS


def test_overload_takes_priority_over_solar() -> None:
    """Overload handling is triggered; solar is not started while over the limit."""
    app_config = _make_app_config()
    em_ctrl = MagicMock()
    em_ctrl.get_consumption.return_value = 7600.0  # ~33A at 230V → over 32A
    app_config._vehicles = []
    overload_handler_mock = MagicMock()

    with patch(
        "tesla_smart_charger.cron.em_cron.overload_handler",
        overload_handler_mock,
    ):
        overload_handler_mock.is_session_active.return_value = False
        overload_handler_mock.trigger_overload.return_value = (True, "started")
        em_cron._check_power_consumption(em_ctrl, app_config)

    assert em_cron.OVERLOAD is True
    overload_handler_mock.trigger_overload.assert_called_once()
    # Solar skipped without a surplus reading.
    assert em_cron.LAST_SURPLUS_AMPS == 0.0


# ─── _start_solar_if_needed ───────────────────────────────────────────────────


def test_start_solar_skipped_when_disabled() -> None:
    """No attempt is made when solar surplus mode is disabled."""
    app_config = _make_app_config(solarSurplusEnabled=False)
    em_cron.LAST_SURPLUS_AMPS = 5.0

    with patch("tesla_smart_charger.cron.em_cron.solar_handler") as mock_solar:
        em_cron._start_solar_if_needed(app_config)

    mock_solar.trigger_solar.assert_not_called()


def test_start_solar_obeys_cooldown() -> None:
    """Attempts are throttled when the cooldown window has not elapsed."""
    app_config = _make_app_config()
    em_cron._last_solar_attempt = 1e18  # far in the future → cooldown active

    with (
        patch("tesla_smart_charger.cron.em_cron.solar_handler") as mock_solar,
        patch("tesla_smart_charger.cron.em_cron.time") as mock_time,
    ):
        mock_time.monotonic.return_value = 1e18 + 10  # 10s since last attempt
        em_cron._start_solar_if_needed(app_config)

    mock_solar.trigger_solar.assert_not_called()


def test_start_solar_fires_after_cooldown() -> None:
    """An attempt is made once the cooldown window has elapsed."""
    app_config = _make_app_config()
    em_cron._last_solar_attempt = 0.0

    with (
        patch("tesla_smart_charger.cron.em_cron.solar_handler") as mock_solar,
        patch("tesla_smart_charger.cron.em_cron.time") as mock_time,
    ):
        mock_time.monotonic.return_value = 60.0
        mock_solar.trigger_solar.return_value = (True, "started")
        mock_solar.is_surplus_active.return_value = False
        em_cron._start_solar_if_needed(app_config)

    mock_solar.trigger_solar.assert_called_once_with(app_config)
