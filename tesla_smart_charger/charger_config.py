"""Configurator class for Tesla Smart Charger."""

import json

from pathlib import Path
from typing import Optional

from tesla_smart_charger import constants


class ChargerConfig:
    """
    Configurator class for Tesla Smart Charger.

    Attributes
    ----------
        config_file (str): str to the configuration file.
        config (dict): The configuration.

    """

    def __init__(self, config_file: str) -> None:
        """
        Initialize the configurator.

        Args:
        ----
            config_file (Path): Path to the configuration file.

        """
        self.config_file = Path(config_file)
        self.config: Optional[dict] = None

    def load_config(self) -> dict:
        """
        Load the configuration file.

        Returns
        -------
                dict: The configuration.

        """
        try:
            with Path.open(self.config_file, "r") as file:
                self.config = json.load(file)
            if not self.config:
                return {"error": "Config file is empty."}
            self.validate_config(self.config)
        except FileNotFoundError as error:
            return {"error": f"Config file not found: {error}"}
        except json.JSONDecodeError as error:
            return {"error": f"Config file is not valid JSON: {error}"}
        except ValueError as error:
            return {"error": f"Config file is not valid: {error}"}
        else:
            return self.config

    def get_config(self) -> dict:
        """
        Return the configuration.

        Returns
        -------
            dict: The configuration.

        """
        return self.config or {}

    def set_config(self, config: dict) -> dict:
        """
        Set the configuration.

        Args:
        ----
            config (dict): The configuration.

        Returns:
        -------
            dict: The configuration.

        """
        try:
            self.validate_config(config)
            with Path.open(self.config_file, "w") as file:
                json.dump(config, file, indent=4)
            self.load_config()
            if self.config is None:
                return {"error": "Failed to load config after setting it."}
        except ValueError as error:
            return {"error": f"Config is not valid: {error}"}
        except Exception as error:
            return {"error": f"Failed to set config: {error}"}
        else:
            return self.config

    @staticmethod
    def validate_config(config: dict) -> None:
        """
        Validate the configuration.

        Args:
        ----
            config (dict): The configuration.

        Raises:
        ------
                SystemExit: If the configuration is not valid.

        """
        for key in constants.REQUIRED_CONFIG_KEYS:
            if key not in config:
                msg = f"Missing required config key: {key}"
                raise ValueError(msg)
