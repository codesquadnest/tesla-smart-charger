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
        config_file (str): Path to the configuration file.
        config (dict): The configuration.

    """

    def __init__(self, config_file: str) -> None:
        """
        Initialize the configurator.

        Args:
        ----
            config_file (str): Path to the configuration file.

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
        # Guard: always return error if config is not loaded
        return self.config if self.config is not None else {"error": "Config not loaded."}

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
            # atomic write: write to temp then replace
            import tempfile
            import os
            tmp_name = None
            with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=str(self.config_file.parent), encoding="utf-8"
            ) as tmp:
                json.dump(config, tmp, indent=4, ensure_ascii=False)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_name = tmp.name
            # Ensure restrictive permissions on the resulting file
            if tmp_name is not None:
                os.chmod(tmp_name, 0o600)
            try:
                os.replace(tmp_name, self.config_file)
            finally:
                if tmp_name and os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            loaded = self.load_config()
            if isinstance(loaded, dict) and "error" in loaded:
                return loaded
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
                ValueError: If the configuration is not valid.

        """
        for key in constants.REQUIRED_CONFIG_KEYS:
            if key not in config:
                msg = f"Missing required config key: {key}"
                raise ValueError(msg)
