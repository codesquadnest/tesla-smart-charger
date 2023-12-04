"""
Configurator class for Tesla Smart Charger.
"""


import json
import pathlib

from pydantic import BaseModel

import tesla_smart_charger.constants as constants


class ChargerConfig:
    """Configurator class for Tesla Smart Charger.

    Attributes:

        config_file (pathlib): Path to the configuration file.
        config (dict): The configuration.

    """

    def __init__(self: object, config_file: pathlib) -> None:
        """Initialize the configurator.

        Args:

            config_file (pathlib): Path to the configuration file.

        """
        self.config_file = config_file
        self.config = None

    def load_config(self: object) -> dict:
        """Load the configuration file.

        Returns:

                dict: The configuration.

        """

        try:
            with open(self.config_file, "r") as file:
                self.config = json.load(file)
            self.validate_config(self.config)
            return self.config
        except FileNotFoundError as error:
            return {"error": f"Config file not found: {error}"}
        except json.JSONDecodeError as error:
            return {"error": f"Config file is not valid JSON: {error}"}
        except ValueError as error:
            return {"error": f"Config file is not valid: {error}"}

    def get_config(self: object) -> dict:
        """Return the configuration.

        Returns:

            dict: The configuration.
        """
        return self.config

    def set_config(self: object, config: BaseModel) -> dict:
        """Set the configuration.
        
        Args:
            config (BaseModel): The configuration.

        Returns:
            dict: The configuration.

        """
        try:
            self.validate_config(config)
            with open(self.config_file, "w") as file:
                file.write(config)
            self.load_config()
            return self.config
        except ValueError as error:
            return {"error": f"Config is not valid: {error}"}

    @staticmethod
    def validate_config(config: dict) -> None:
        """Validate the configuration.

        Args:
            config (dict): The configuration.

            Raises:
                SystemExit: If the configuration is not valid.

        """
        for key in constants.REQUIRED_CONFIG_KEYS:
            if key not in config:
                raise ValueError(f"Config file is missing required key: {key}")
