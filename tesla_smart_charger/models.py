"""Pydantic models for Tesla Smart Charger configuration."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TeslaRegion(str, Enum):
    """Supported Tesla Fleet API regions."""

    EU = "eu"
    NA = "na"
    AP = "ap"


class OverloadStrategy(str, Enum):
    """Strategy for distributing load reduction across multiple vehicles."""

    PROPORTIONAL = "proportional"  # All vehicles reduced proportionally
    PRIORITY = "priority"  # Vehicles reduced in priority order (1 = highest, reduce last)


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
    hostIp: str = "localhost"
    apiPort: int = 8000
    corsOrigins: List[str] = Field(default_factory=lambda: ["*"])
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
    online: Optional[bool] = None
    chargingState: Optional[str] = None
    chargerActualCurrent: Optional[float] = None
    batteryLevel: Optional[int] = None


class SystemStatus(BaseModel):
    """Overall system status returned by GET /api/v1/status."""

    configured: bool
    monitorActive: bool
    overloadActive: bool
    currentConsumptionAmps: Optional[float] = None
    homeMaxAmps: float
    region: str
    voltage: float
    vehicles: list[VehicleStatus] = Field(default_factory=list)
