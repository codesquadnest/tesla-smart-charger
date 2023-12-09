"""
Test the overload handler
"""

import pytest

from unittest.mock import patch

import tesla_smart_charger.handlers.overload_handler as overload_handler


@pytest.mark.parametrize(
    "current_charge_limit, current_em_consumption, max_charge_limit, min_charge_limit, house_max_power, expected_new_charge_limit",
    [
        (16, 16, 16, 6, 16, 16),
        (15, 17, 16, 6, 16, 14),
        (15, 18, 16, 6, 16, 13),
        (12, 15, 16, 6, 16, 13),
        (20, 27, 25, 6, 32, 25),
        (25, 35, 25, 6, 32, 22)
    ],
)
@patch(
    "tesla_smart_charger.handlers.overload_handler.tesla_config.config",
    {"downStepPercentage": 0.5},
)
def test_calculate_new_charge_limit(
    current_charge_limit: float,
    current_em_consumption: float,
    max_charge_limit: float,
    min_charge_limit: float,
    house_max_power: float,
    expected_new_charge_limit: float,
) -> None:
    """
    Test calculating the new charge limit
    """
    assert (
        overload_handler._calculate_new_charge_limit(
            current_charge_limit,
            current_em_consumption,
            max_charge_limit,
            min_charge_limit,
            house_max_power,
        )
        == expected_new_charge_limit
    )
