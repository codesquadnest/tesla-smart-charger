"""Tests for the charger_config module."""

import json
import pathlib

import pytest
from pydantic import BaseModel

from tesla_smart_charger.charger_config import ChargerConfig


@pytest.fixture()
def config_file(tmp_path: str) -> str:
    """Create a temporary config file."""
    config = {
        "homeMaxAmps": "11.0",
        "chargerMaxAmps": "11.0",
        "chargerMinAmps": "6.0",
        "downStepPercentage": "0.5",
        "upStepPercentage": "0.5",
        "sleepTimeSecs": "300",
        "energyMonitorIp": "localhost",
        "energyMonitorType": "shell_em",
        "teslaVehicleId": "1234567890",
        "teslaAccessToken": "1234567890",
        "teslaRefreshToken": "0987654321",
        "teslaHttpProxy": "https://localhost:4443",
        "teslaClientId": "12234567890",
    }
    config_file = tmp_path / "config.json"
    with pathlib.Path.open(pathlib.Path(config_file), "w") as file:
        json.dump(config, file, indent=4)
    return config_file


def test_load_config(config_file: str) -> None:
    """Test loading the config file."""
    tesla_config = ChargerConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.get_config() == {
        "homeMaxAmps": "11.0",
        "chargerMaxAmps": "11.0",
        "chargerMinAmps": "6.0",
        "downStepPercentage": "0.5",
        "upStepPercentage": "0.5",
        "sleepTimeSecs": "300",
        "energyMonitorIp": "localhost",
        "energyMonitorType": "shell_em",
        "teslaVehicleId": "1234567890",
        "teslaAccessToken": "1234567890",
        "teslaRefreshToken": "0987654321",
        "teslaHttpProxy": "https://localhost:4443",
        "teslaClientId": "12234567890",
    }


def test_load_config_file_not_found() -> None:
    """Test loading a config file that does not exist."""
    tesla_config = ChargerConfig("missing_config.json")
    assert tesla_config.load_config()["error"].startswith("Config file not found:")


def test_load_config_file_not_valid_json(tmp_path: str) -> None:
    """Test loading a config file that is not valid JSON."""
    config_file = tmp_path / "config.json"
    with pathlib.Path.open(pathlib.Path(config_file), "w") as file:
        file.write("not valid json")
    tesla_config = ChargerConfig(config_file)
    assert tesla_config.load_config()["error"].startswith(
        "Config file is not valid JSON:",
    )


def test_load_config_file_missing_required_key(tmp_path: str) -> None:
    """Test loading a config file that is missing a required key."""
    config_file = tmp_path / "config.json"
    with pathlib.Path.open(pathlib.Path(config_file), "w") as file:
        json.dump({"chargerMaxAmps": 11.0}, file, indent=4)
    tesla_config = ChargerConfig(config_file)
    assert tesla_config.load_config()["error"].startswith(
        "Config file is not valid: Missing required config key: homeMaxAmps",
    )


def test_get_config(config_file: str) -> None:
    """Test getting the config."""
    tesla_config = ChargerConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.get_config() == {
        "homeMaxAmps": "11.0",
        "chargerMaxAmps": "11.0",
        "chargerMinAmps": "6.0",
        "downStepPercentage": "0.5",
        "upStepPercentage": "0.5",
        "sleepTimeSecs": "300",
        "energyMonitorIp": "localhost",
        "energyMonitorType": "shell_em",
        "teslaVehicleId": "1234567890",
        "teslaAccessToken": "1234567890",
        "teslaRefreshToken": "0987654321",
        "teslaHttpProxy": "https://localhost:4443",
        "teslaClientId": "12234567890",
    }


def test_set_config(config_file: str) -> None:
    """Test setting the config."""
    tesla_config = ChargerConfig(config_file)
    tesla_config.load_config()

    class Config(BaseModel):

        """Config class for Tesla Smart Charger."""

        homeMaxAmps: float
        chargerMaxAmps: float
        chargerMinAmps: float
        downStepPercentage: float
        upStepPercentage: float
        sleepTimeSecs: int
        energyMonitorIp: str
        energyMonitorType: str
        teslaVehicleId: str
        teslaAccessToken: str
        teslaRefreshToken: str
        teslaHttpProxy: str
        teslaClientId: str

    test_config = Config(
        homeMaxAmps=11.0,
        chargerMaxAmps=10.0,
        chargerMinAmps=5.0,
        downStepPercentage=0.5,
        upStepPercentage=0.5,
        sleepTimeSecs=300,
        energyMonitorIp="localhost",
        energyMonitorType="shell_em",
        teslaVehicleId="1234567890",
        teslaAccessToken="1234567890",
        teslaRefreshToken="0987654321",
        teslaHttpProxy="https://localhost:4443",
        teslaClientId="12234567890",
    )

    tesla_config.set_config(test_config.model_dump_json())
    assert tesla_config.get_config() == {
        "homeMaxAmps": 11.0,
        "chargerMaxAmps": 10.0,
        "chargerMinAmps": 5.0,
        "downStepPercentage": 0.5,
        "upStepPercentage": 0.5,
        "sleepTimeSecs": 300,
        "energyMonitorIp": "localhost",
        "energyMonitorType": "shell_em",
        "teslaVehicleId": "1234567890",
        "teslaAccessToken": "1234567890",
        "teslaRefreshToken": "0987654321",
        "teslaHttpProxy": "https://localhost:4443",
        "teslaClientId": "12234567890",
    }


def test_set_config_missing_required_key(config_file: str) -> None:
    """Test setting the config with a config that is missing a required key."""
    tesla_config = ChargerConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.set_config({"chargerMaxAmps": 11.0})["error"].startswith(
        "Config is not valid: Missing required config key: homeMaxAmps",
    )


def test_validate_config() -> None:
    """Test validating a config."""
    tesla_config = ChargerConfig("config.json")
    tesla_config.load_config()
    tesla_config.validate_config(
        {
            "homeMaxAmps": 11.0,
            "chargerMaxAmps": 11.0,
            "chargerMinAmps": 6.0,
            "downStepPercentage": 0.5,
            "upStepPercentage": 0.5,
            "sleepTimeSecs": 300,
            "energyMonitorIp": "localhost",
            "energyMonitorType": "shell_em",
            "teslaVehicleId": "1234567890",
            "teslaAccessToken": "1234567890",
            "teslaRefreshToken": "0987654321",
            "teslaHttpProxy": "https://localhost:4443",
            "teslaClientId": "12234567890",
        },
    )
    with pytest.raises(ValueError): # noqa: PT011
        tesla_config.validate_config({"chargerMaxAmps": 11.0, "chargerMinAmps": 6.0})
    with pytest.raises(ValueError): # noqa: PT011
        tesla_config.validate_config(
            {"chargerMaxAmps": 11.0, "chargerMinAmps": 6.0, "downStepPercentage": 0.5},
        )
    with pytest.raises(ValueError): # noqa: PT011
        tesla_config.validate_config(
            {
                "chargerMaxAmps": 11.0,
                "chargerMinAmps": 6.0,
                "downStepPercentage": 0.5,
                "upStepPercentage": 0.5,
            },
        )
