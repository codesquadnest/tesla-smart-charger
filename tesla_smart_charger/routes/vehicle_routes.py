"""Vehicle CRUD endpoints — /api/v1/vehicles."""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tesla_smart_charger import logger, telemetry_cache
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.models import VehicleConfig
from tesla_smart_charger.tesla_api import TeslaAPI

tsc_logger = logger.get_logger()

router = APIRouter(prefix="/api/v1/vehicles", tags=["vehicles"])

_app_config: AppConfig | None = None


def init(app_config: AppConfig) -> None:
    """Inject the shared AppConfig instance used by this router."""
    global _app_config
    _app_config = app_config


class VehicleCreate(BaseModel):
    """Body for adding a new vehicle."""

    name: str = ""
    vin: str
    teslaVehicleId: str
    teslaAccessToken: str
    teslaRefreshToken: str
    teslaHttpProxy: str
    teslaClientId: str
    region: str = "eu"
    chargerMaxAmps: float = 25.0
    chargerMinAmps: float = 6.0
    priority: int = 1
    enabled: bool = True


class VehicleUpdate(BaseModel):
    """Partial vehicle update — all fields optional."""

    name: str | None = None
    chargerMaxAmps: float | None = None
    chargerMinAmps: float | None = None
    priority: int | None = None
    enabled: bool | None = None
    teslaHttpProxy: str | None = None
    teslaClientId: str | None = None


def _redact(v: VehicleConfig) -> dict:
    """Return vehicle dict with tokens replaced by redaction markers."""
    d = v.model_dump()
    d["teslaAccessToken"] = "***" if d["teslaAccessToken"] else ""
    d["teslaRefreshToken"] = "***" if d["teslaRefreshToken"] else ""
    return d


@router.get("")
def list_vehicles() -> JSONResponse:
    """List all configured vehicles, with tokens redacted."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    return JSONResponse([_redact(v) for v in _app_config.vehicles], status_code=200)


@router.post("")
def add_vehicle(body: VehicleCreate) -> JSONResponse:
    """Add a new managed vehicle."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    vehicle = VehicleConfig(**body.model_dump())
    added = _app_config.add_vehicle(vehicle)
    return JSONResponse(_redact(added), status_code=201)


@router.get("/{vehicle_id}")
def get_vehicle(vehicle_id: str) -> JSONResponse:
    """Return a single vehicle by id, with tokens redacted."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    vehicle = _app_config.get_vehicle(vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
    return JSONResponse(_redact(vehicle), status_code=200)


@router.patch("/{vehicle_id}")
def patch_vehicle(vehicle_id: str, body: VehicleUpdate) -> JSONResponse:
    """Apply a partial update to a vehicle's configuration."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    updates: dict[str, Any] = {
        k: v for k, v in body.model_dump().items() if v is not None
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    updated = _app_config.update_vehicle(vehicle_id, updates)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
    # Cached statuses embed config fields (name, amp limits, priority, enabled),
    # so a stale entry would keep serving pre-update values for up to the TTL.
    telemetry_cache.invalidate(vehicle_id)
    return JSONResponse(_redact(updated), status_code=200)


@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: str) -> JSONResponse:
    """Remove a vehicle from the configuration."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    removed = _app_config.remove_vehicle(vehicle_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
    telemetry_cache.invalidate(vehicle_id)
    return JSONResponse({"message": f"Vehicle {vehicle_id} removed."}, status_code=200)


@router.get("/{vehicle_id}/tesla-vehicles")
def list_tesla_vehicles(vehicle_id: str) -> JSONResponse:
    """
    Fetch the list of Tesla vehicles linked to the given vehicle's OAuth token.

    Useful for onboarding: select a vehicle from the account.
    """
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    vehicle = _app_config.get_vehicle(vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=404, detail=f"Vehicle config {vehicle_id} not found"
        )
    try:
        api = TeslaAPI(vehicle)
        tesla_vehicles = api.get_vehicles()
        return JSONResponse({"vehicles": tesla_vehicles}, status_code=200)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
