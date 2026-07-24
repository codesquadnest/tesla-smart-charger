"""Application configuration manager for Tesla Smart Charger."""

import json
import uuid
from pathlib import Path
from typing import Any

from tesla_smart_charger import logger
from tesla_smart_charger.models import (
    AuthConfig,
    SystemConfig,
    TeslaRegion,
    VehicleConfig,
)

tsc_logger = logger.get_logger()


class AppConfig:
    """
    Application configuration manager.

    Handles loading, saving, and migrating configuration.
    Stores system-wide settings in ``config/system.json`` and
    per-vehicle credentials & settings in ``config/vehicles.json``.

    On first run it automatically migrates an existing ``config.json``
    (legacy flat format) to the new structured layout.
    """

    def __init__(self, config_dir: str = "config") -> None:
        """Bind this manager to *config_dir* (not loaded until `load()` is called)."""
        self._config_dir = Path(config_dir)
        self._system_file = self._config_dir / "system.json"
        self._vehicles_file = self._config_dir / "vehicles.json"
        self._legacy_file = Path("config.json")
        self._system: SystemConfig | None = None
        self._vehicles: list[VehicleConfig] = []

    # ─── Properties ───────────────────────────────────────────────────────────

    @property
    def system(self) -> SystemConfig:
        """Return the loaded system configuration."""
        if self._system is None:
            msg = "Configuration not loaded. Call load() first."
            raise RuntimeError(msg)
        return self._system

    @property
    def vehicles(self) -> list[VehicleConfig]:
        """Return the loaded list of vehicle configurations."""
        return self._vehicles

    @property
    def is_configured(self) -> bool:
        """Return whether the onboarding wizard has been completed."""
        return self._system is not None and self._system.configured

    # ─── Load ─────────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load configuration; auto-migrates legacy config.json when needed."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        if self._legacy_file.exists() and not self._system_file.exists():
            tsc_logger.info("Legacy config.json detected — migrating to new format.")
            self._migrate_from_legacy()
        else:
            self._load_system()
            self._load_vehicles()

    def _load_system(self) -> None:
        try:
            with self._system_file.open("r") as f:
                data = json.load(f)
            # Handle nested auth dict
            if "auth" in data and isinstance(data["auth"], dict):
                data["auth"] = AuthConfig(**data["auth"])
            self._system = SystemConfig(**data)
        except FileNotFoundError:
            tsc_logger.info("system.json not found — using defaults.")
            self._system = SystemConfig()
        # Deliberately broad: any load/parse failure must fall back to
        # defaults rather than prevent the app from starting.
        except Exception:
            tsc_logger.exception("Failed to load system.json")
            self._system = SystemConfig()

    def _load_vehicles(self) -> None:
        try:
            with self._vehicles_file.open("r") as f:
                raw = json.load(f)
            self._vehicles = [VehicleConfig(**v) for v in raw]
        except FileNotFoundError:
            tsc_logger.info(
                "vehicles.json not found — starting with empty vehicle list."
            )
            self._vehicles = []
        # Deliberately broad: any load/parse failure must fall back to
        # an empty vehicle list rather than prevent the app from starting.
        except Exception:
            tsc_logger.exception("Failed to load vehicles.json")
            self._vehicles = []

    def _migrate_from_legacy(self) -> None:
        """Migrate the old flat config.json → system.json + vehicles.json."""
        try:
            with self._legacy_file.open("r") as f:
                old: dict[str, Any] = json.load(f)
        # Deliberately broad: a corrupt/unreadable legacy file must fall back
        # to defaults rather than prevent the app from starting.
        except Exception:
            tsc_logger.exception("Migration failed — could not read config.json")
            self._system = SystemConfig()
            return

        def _f(key: str, default: float) -> float:
            try:
                return float(old.get(key, default))
            except (TypeError, ValueError):
                return default

        def _i(key: str, default: int) -> int:
            try:
                return int(float(old.get(key, default)))
            except (TypeError, ValueError):
                return default

        self._system = SystemConfig(
            homeMaxAmps=_f("homeMaxAmps", 30.0),
            voltage=230.0,  # EU default; user can change after migration
            region=TeslaRegion.EU,
            energyMonitorIp=old.get("energyMonitorIp", ""),
            energyMonitorType=old.get("energyMonitorType", "shelly_em"),
            sleepTimeSecs=_i("sleepTimeSecs", 30),
            downStepPercentage=_f("downStepPercentage", 0.5),
            upStepPercentage=_f("upStepPercentage", 0.25),
            hostIp=old.get("hostIp", "localhost"),
            apiPort=_i("apiPort", 8000),
            configured=True,  # existing config.json means onboarding was already done
        )

        vehicle = VehicleConfig(
            id=str(uuid.uuid4()),
            name="My Tesla",
            teslaVehicleId=str(old.get("teslaVehicleId", "")),
            teslaAccessToken=old.get("teslaAccessToken", ""),
            teslaRefreshToken=old.get("teslaRefreshToken", ""),
            teslaHttpProxy=old.get("teslaHttpProxy", ""),
            teslaClientId=old.get("teslaClientId", ""),
            chargerMaxAmps=_f("chargerMaxAmps", 25.0),
            chargerMinAmps=_f("chargerMinAmps", 6.0),
            priority=1,
        )
        self._vehicles = [vehicle]

        self.save_system()
        self.save_vehicles()
        tsc_logger.info(
            "Migration complete. New config files written to %s/", self._config_dir
        )

    # ─── Save ─────────────────────────────────────────────────────────────────

    def save_system(self) -> None:
        """Persist system configuration to system.json."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with self._system_file.open("w") as f:
            json.dump(self._system.model_dump(), f, indent=2)

    def save_vehicles(self) -> None:
        """Persist vehicle list to vehicles.json."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with self._vehicles_file.open("w") as f:
            json.dump([v.model_dump() for v in self._vehicles], f, indent=2)

    # ─── Vehicle CRUD ──────────────────────────────────────────────────────────

    def get_vehicle(self, vehicle_id: str) -> VehicleConfig | None:
        """Return the vehicle with *vehicle_id*, or None if not found."""
        for v in self._vehicles:
            if v.id == vehicle_id:
                return v
        return None

    def add_vehicle(self, vehicle: VehicleConfig) -> VehicleConfig:
        """Append *vehicle* to the vehicle list and persist it."""
        self._vehicles.append(vehicle)
        self.save_vehicles()
        return vehicle

    def update_vehicle(
        self, vehicle_id: str, updates: dict[str, Any]
    ) -> VehicleConfig | None:
        """Apply *updates* to the vehicle with *vehicle_id* and persist it."""
        for i, v in enumerate(self._vehicles):
            if v.id == vehicle_id:
                updated = v.model_copy(update=updates)
                self._vehicles[i] = updated
                self.save_vehicles()
                return updated
        return None

    def remove_vehicle(self, vehicle_id: str) -> bool:
        """Remove the vehicle with *vehicle_id*; return whether it was found."""
        original_len = len(self._vehicles)
        self._vehicles = [v for v in self._vehicles if v.id != vehicle_id]
        if len(self._vehicles) < original_len:
            self.save_vehicles()
            return True
        return False

    def update_vehicle_tokens(
        self, vehicle_id: str, access_token: str, refresh_token: str
    ) -> None:
        """Atomically update OAuth tokens for a specific vehicle."""
        self.update_vehicle(
            vehicle_id,
            {"teslaAccessToken": access_token, "teslaRefreshToken": refresh_token},
        )

    # ─── System helpers ────────────────────────────────────────────────────────

    def update_system(self, updates: dict[str, Any]) -> SystemConfig:
        """Merge *updates* into the system config and persist."""
        current = self._system.model_dump()
        # Handle nested auth updates
        if "auth" in updates and isinstance(updates["auth"], dict):
            current["auth"].update(updates.pop("auth"))
        current.update(updates)
        self._system = SystemConfig(**current)
        self.save_system()
        return self._system

    def mark_configured(self) -> None:
        """Mark the setup as completed (called after onboarding wizard finishes)."""
        self._system = self._system.model_copy(update={"configured": True})
        self.save_system()
