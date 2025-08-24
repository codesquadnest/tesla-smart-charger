"""Test the overload handler."""

from unittest.mock import MagicMock, patch

import pytest

from tesla_smart_charger.handlers import overload_handler


@pytest.mark.parametrize(
    "current_charge_limit, current_em_consumption, max_charge_limit, min_charge_limit, house_max_power, expected_new_charge_limit",  # noqa: E501, PT006
    [
        (16, 16, 16, 6, 16, 16),
        (15, 17, 16, 6, 16, 14),
        (15, 18, 16, 6, 16, 13),
        (12, 15, 16, 6, 16, 13),
        (20, 27, 25, 6, 32, 25),
        (25, 35, 25, 6, 32, 22),
    ],
)
@patch(
    "tesla_smart_charger.handlers.overload_handler.tesla_config.config",
    {"downStepPercentage": 0.5},
)
def test_calculate_new_charge_limit(  # noqa: PLR0913
    current_charge_limit: float,
    current_em_consumption: float,
    max_charge_limit: float,
    min_charge_limit: float,
    house_max_power: float,
    expected_new_charge_limit: float,
) -> None:
    """Test calculating the new charge limit."""
    assert (
        overload_handler._calculate_new_charge_limit(  # noqa: SLF001
            current_charge_limit,
            current_em_consumption,
            max_charge_limit,
            min_charge_limit,
            house_max_power,
        )
        == expected_new_charge_limit
    )


def test_reload_config() -> None:
    """Test reloading the config."""
    with patch.object(
        overload_handler, "tesla_config", autospec=True
    ) as mock_charger_config:
        overload_handler._reload_config()
        mock_charger_config.load_config.assert_called_once()


def test_init_db_controller() -> None:
    """Test initializing the database controller."""
    with patch(
        "tesla_smart_charger.handlers.overload_handler.db_controller.create_database_controller"
    ) as mock_create_db_controller:
        overload_handler._init_db_controller()
        mock_create_db_controller.assert_called_once_with(
            "sqlite", "tesla_smart_charger", "tesla_smart_charger.db"
        )


def test_init_db_controller_already_initialized() -> None:
    """Test initializing the database controller when it is already initialized."""
    with patch(
        "tesla_smart_charger.handlers.overload_handler.db_controller.create_database_controller"
    ) as mock_create_db_controller:
        overload_handler._init_db_controller()
        first_db_controller = overload_handler.controller_db
        overload_handler._init_db_controller()
        # Verify create_database_controller was only called once
        mock_create_db_controller.assert_called()
        assert overload_handler.controller_db == first_db_controller


def test_finish_overload_handling() -> None:
    """Test finishing the overload handling."""
    with patch(
        "tesla_smart_charger.handlers.overload_handler.db_controller.create_database_controller"
    ):
        with patch("time.strftime") as mock_strftime:
            start_time = "2023-01-01 12:00:00"
            end_time = "2023-01-01 12:01:30"  # 90 seconds later
            mock_strftime.return_value = end_time
            overload_handler._finish_overload_handling(start_time)
            # Verify the data inserted includes the correct duration in seconds
            overload_handler.controller_db.insert_data.assert_called_once_with(
                {"start": start_time, "end": end_time, "duration": "90.0"}
            )
        overload_handler.controller_db.close_connection.assert_called_once()


def test_get_current_consumption_in_amps() -> None:
    """Test getting the current consumption in amps."""
    with patch(
        "tesla_smart_charger.handlers.overload_handler.tsc_logger", autospec=True
    ) as mock_logger:
        # Create a MagicMock with the get_consumption method
        mock_em_controller = MagicMock()
        mock_em_controller.get_consumption.return_value = 230

        # Call the function with the mock object
        result = overload_handler._get_current_consumption_in_amps(mock_em_controller)
        assert result == 1.0

        mock_logger.debug.assert_called_once_with("Current consumption in amps: 1.00")


def test_get_current_consumption_in_amps_error() -> None:
    """Test getting the current consumption in amps when an error occurs."""
    with patch(
        "tesla_smart_charger.handlers.overload_handler.tsc_logger", autospec=True
    ) as mock_logger:
        # Create a MagicMock with the get_consumption method
        mock_em_controller = MagicMock()
        mock_em_controller.get_consumption.side_effect = ValueError("Test error")

        # Call the function with the mock object
        result = overload_handler._get_current_consumption_in_amps(mock_em_controller)
        assert result == 0.0

        mock_logger.error.assert_called_once_with(
            "Error getting consumption: Test error"
        )
