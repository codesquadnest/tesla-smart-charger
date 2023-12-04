"""
Tests for the charger_config module.
"""

import json

from pydantic import BaseModel

import pytest

from tesla_smart_charger.charger_config import ChargerConfig


@pytest.fixture
def config_file(tmp_path: str) -> str:
    """
    Create a temporary config file.
    """
    config = {
        "maxPower": 11.0,
        "minPower": 6.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "vehicleId": "1234567890",
        "accessToken": "1234567890",
        "refreshToken": "0987654321",
    }
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as file:
        json.dump(config, file, indent=4)
    return config_file


def test_load_config(config_file: str) -> None:
    """
    Test loading the config file.
    """
    tesla_config = ChargerConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.get_config() == {
        "maxPower": 11.0,
        "minPower": 6.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "vehicleId": "1234567890",
        "accessToken": "1234567890",
        "refreshToken": "0987654321",
    }


def test_load_config_file_not_found() -> None:
    """
    Test loading a config file that does not exist.
    """
    tesla_config = ChargerConfig("missing_config.json")
    assert tesla_config.load_config()["error"].startswith("Config file not found:")


def test_load_config_file_not_valid_json(tmp_path: str) -> None:
    """
    Test loading a config file that is not valid JSON.
    """
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as file:
        file.write("not valid json")
    tesla_config = ChargerConfig(config_file)
    assert tesla_config.load_config()["error"].startswith(
        "Config file is not valid JSON:"
    )


def test_load_config_file_missing_required_key(tmp_path: str) -> None:
    """
    Test loading a config file that is missing a required key.
    """
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as file:
        json.dump({"maxPower": 11.0}, file, indent=4)
    tesla_config = ChargerConfig(config_file)
    assert tesla_config.load_config()["error"].startswith(
        "Config file is not valid: Config file is missing required key: minPower"
    )


def test_get_config(config_file: str) -> None:
    """
    Test getting the config.
    """
    tesla_config = ChargerConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.get_config() == {
        "maxPower": 11.0,
        "minPower": 6.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "vehicleId": "1234567890",
        "accessToken": "1234567890",
        "refreshToken": "0987654321",
    }


def test_set_config(config_file: str) -> None:
    """
    Test setting the config.
    """
    tesla_config = ChargerConfig(config_file)
    tesla_config.load_config()

    class Config(BaseModel):
        """Config class for Tesla Smart Charger."""

        maxPower: float
        minPower: float
        downStep: float
        upStep: float
        vehicleId: str
        accessToken: str
        refreshToken: str

    test_config = Config(
        maxPower=10.0,
        minPower=5.0,
        downStep=0.5,
        upStep=0.5,
        vehicleId="1234567890",
        accessToken="1234567890",
        refreshToken="0987654321",
    )

    tesla_config.set_config(test_config.model_dump_json())
    assert tesla_config.get_config() == {
        "maxPower": 10.0,
        "minPower": 5.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "vehicleId": "1234567890",
        "accessToken": "1234567890",
        "refreshToken": "0987654321",
    }


def test_set_config_missing_required_key(config_file: str) -> None:
    """
    Test setting the config with a config that is missing a required key.
    """
    tesla_config = ChargerConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.set_config({"maxPower": 11.0})["error"].startswith(
        "Config is not valid: Config file is missing required key: minPower"
    )


def test_validate_config() -> None:
    """
    Test validating a config.
    """
    tesla_config = ChargerConfig("config.json")
    tesla_config.load_config()
    tesla_config.validate_config(
        {
            "maxPower": 11.0,
            "minPower": 6.0,
            "downStep": 0.5,
            "upStep": 0.5,
            "vehicleId": "1234567890",
            "accessToken": "1234567890",
            "refreshToken": "0987654321",
        }
    )
    with pytest.raises(ValueError):
        tesla_config.validate_config({"maxPower": 11.0, "minPower": 6.0})
    with pytest.raises(ValueError):
        tesla_config.validate_config(
            {"maxPower": 11.0, "minPower": 6.0, "downStep": 0.5}
        )
    with pytest.raises(ValueError):
        tesla_config.validate_config(
            {"maxPower": 11.0, "minPower": 6.0, "downStep": 0.5, "upStep": 0.5}
        )
