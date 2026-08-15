"""Pydantic models for Tesla Smart Charger configuration."""

from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class TeslaRegion(str, Enum):
    """Supported Tesla Fleet API regions."""

    EU = "eu"
    NA = "na"
    AP = "ap"


class OverloadStrategy(str, Enum):
    """Strategy for distributing load reduction across multiple vehicles."""

    PROPORTIONAL = "proportional"  # All vehicles reduced proportionally
    PRIORITY = (
        "priority"  # Vehicles reduced in priority order (1 = highest, reduce last)
    )


class AuthConfig(BaseModel):
    """Optional HTTP Basic Auth configuration."""

    enabled: bool = False
    username: str = ""
    passwordHash: str = ""  # bcrypt hash, empty means no auth


class VehicleConfig(BaseModel):
    """Configuration and credentials for a single managed Tesla vehicle."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    vin: str = ""
    teslaVehicleId: str = ""
    teslaAccessToken: str = ""
    teslaRefreshToken: str = ""
    teslaHttpProxy: str = ""
    teslaClientId: str = ""
    region: str = "eu"
    chargerMaxAmps: float = 25.0
    chargerMinAmps: float = 6.0
    priority: int = 1  # 1 = highest priority (reduced last in priority strategy)
    enabled: bool = True


class SystemConfig(BaseModel):
    """System-wide application configuration."""

    homeMaxAmps: float = 30.0
    voltage: float = 230.0
    region: TeslaRegion = TeslaRegion.EU
    energyMonitorIp: str = ""
    energyMonitorType: str = "shelly_em"
    sleepTimeSecs: int = 30
    downStepPercentage: float = 0.5
    upStepPercentage: float = 0.25
    overloadStrategy: OverloadStrategy = OverloadStrategy.PROPORTIONAL
    maxSessionDuration: int = (
        600  # Maximum supervised session duration in seconds (default 10 min)
    )
    # Solar surplus charging: when enabled the solar handler tracks the grid
    # feed-in (negative EM reading = exporting) and sizes charging current to
    # absorb it, keeping grid import at/under solarTargetAmps.
    solarSurplusEnabled: bool = False
    solarTargetAmps: float = 1.0  # Desired grid import while in solar mode (A)
    hostIp: str = "localhost"
    apiPort: int = 8000
    corsOrigins: list[str] = Field(default_factory=lambda: ["*"])
    auth: AuthConfig = Field(default_factory=AuthConfig)
    configured: bool = False  # Set to True after completing the onboarding wizard


# ─── API response models ───────────────────────────────────────────────────────


class VehicleStatus(BaseModel):
    """Live status for a vehicle, merged with its config."""

    id: str
    name: str
    vin: str
    teslaVehicleId: str
    teslaHttpProxy: str
    chargerMaxAmps: float
    chargerMinAmps: float
    priority: int
    enabled: bool
    # Live fields (None when vehicle is offline / not reachable)
    online: bool | None = None
    chargingState: str | None = None
    chargerActualCurrent: float | None = None
    batteryLevel: int | None = None
    chargeLimitSoc: int | None = None
    # True while telemetry has never been fetched yet and a background
    # refresh is in flight — lets clients distinguish "still fetching"
    # from "checked and it's offline".
    pending: bool = False
    # Seconds since this vehicle's telemetry was fetched from Tesla, computed
    # server-side (the cache stores a process-relative time.monotonic() value).
    # None when nothing has ever been fetched.
    telemetryAgeSecs: float | None = None
    # True whenever a background refresh is in flight, unlike `pending` which
    # only covers the very first fetch.
    refreshing: bool = False


class SystemStatus(BaseModel):
    """Overall system status returned by GET /api/v1/status."""

    configured: bool
    monitorActive: bool
    overloadActive: bool
    # Whether a solar surplus-tracking session is currently active.
    solarActive: bool = False
    # Whether solar surplus mode is configured/enabled.
    solarSurplusEnabled: bool = False
    # Current surplus export in amps (0 when consuming or not metered).
    currentSurplusAmps: float | None = None
    # Whether Basic Auth is configured. Vehicle command endpoints fail closed
    # without it, so the dashboard uses this to lock its controls and explain why.
    authEnabled: bool = False
    currentConsumptionAmps: float | None = None
    homeMaxAmps: float
    region: str
    voltage: float
    vehicles: list[VehicleStatus] = Field(default_factory=list)
