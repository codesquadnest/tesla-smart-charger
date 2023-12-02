"""
Tests for the tesla_config module.
"""

import json

import pytest

from tesla_smart_charger.tesla_config import TeslaConfig


@pytest.fixture
def config_file(tmp_path):
    """
    Create a temporary config file.
    """
    config = {
        "maxPower": 11.0,
        "minPower": 6.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "teslaToken": "1234567890",
    }
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as file:
        json.dump(config, file, indent=4)
    return config_file


def test_load_config(config_file):
    """
    Test loading the config file.
    """
    tesla_config = TeslaConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.get_config() == {
        "maxPower": 11.0,
        "minPower": 6.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "teslaToken": "1234567890",
    }


def test_load_config_file_not_found():
    """
    Test loading a config file that does not exist.
    """
    tesla_config = TeslaConfig("missing_config.json")
    assert tesla_config.load_config()["error"].startswith("Config file not found:")


def test_load_config_file_not_valid_json(tmp_path):
    """
    Test loading a config file that is not valid JSON.
    """
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as file:
        file.write("not valid json")
    tesla_config = TeslaConfig(config_file)
    assert tesla_config.load_config()["error"].startswith(
        "Config file is not valid JSON:"
    )


def test_load_config_file_missing_required_key(tmp_path):
    """
    Test loading a config file that is missing a required key.
    """
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as file:
        json.dump({"maxPower": 11.0}, file, indent=4)
    tesla_config = TeslaConfig(config_file)
    assert tesla_config.load_config()["error"].startswith(
        "Config file is not valid: Config file is missing required key: minPower"
    )

def test_get_config(config_file):
    """
    Test getting the config.
    """
    tesla_config = TeslaConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.get_config() == {
        "maxPower": 11.0,
        "minPower": 6.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "teslaToken": "1234567890",
    }


def test_set_config(config_file):
    """
    Test setting the config.
    """
    tesla_config = TeslaConfig(config_file)
    tesla_config.load_config()
    tesla_config.set_config(
        {
            "maxPower": 10.0,
            "minPower": 5.0,
            "downStep": 0.5,
            "upStep": 0.5,
            "teslaToken": "1234567890",
        }
    )
    assert tesla_config.get_config() == {
        "maxPower": 10.0,
        "minPower": 5.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "teslaToken": "1234567890",
    }
    tesla_config.set_config(
        {
            "maxPower": 11.0,
            "minPower": 6.0,
            "downStep": 0.5,
            "upStep": 0.5,
            "teslaToken": "1234567890",
        }
    )
    assert tesla_config.get_config() == {
        "maxPower": 11.0,
        "minPower": 6.0,
        "downStep": 0.5,
        "upStep": 0.5,
        "teslaToken": "1234567890",
    }


def test_set_config_missing_required_key(config_file):
    """
    Test setting the config with a config that is missing a required key.
    """
    tesla_config = TeslaConfig(config_file)
    tesla_config.load_config()
    assert tesla_config.set_config({"maxPower": 11.0})["error"].startswith(
        "Config is not valid: Config file is missing required key: minPower"
    )


def test_validate_config():
    """
    Test validating a config.
    """
    tesla_config = TeslaConfig("config.json")
    tesla_config.load_config()
    tesla_config.validate_config(
        {
            "maxPower": 11.0,
            "minPower": 6.0,
            "downStep": 0.5,
            "upStep": 0.5,
            "teslaToken": "1234567890",
        }
    )
    with pytest.raises(ValueError):
        tesla_config.validate_config({"maxPower": 11.0, "minPower": 6.0})
    with pytest.raises(ValueError):
        tesla_config.validate_config({"maxPower": 11.0, "minPower": 6.0, "downStep": 0.5})
    with pytest.raises(ValueError):
        tesla_config.validate_config(
            {"maxPower": 11.0, "minPower": 6.0, "downStep": 0.5, "upStep": 0.5}
        )
