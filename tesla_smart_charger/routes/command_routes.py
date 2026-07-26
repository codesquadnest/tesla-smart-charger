"""
Vehicle command endpoints — /api/v1/vehicles/{id}/...

Commands that change vehicle state invalidate the telemetry cache so the
dashboard refetches instead of showing pre-command values for up to the
cache TTL.

Every route here has physical-world effects, so the whole router sits behind
``security.require_auth`` — which fails closed when Basic Auth has not been
configured.  See `tesla_smart_charger/security.py`.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from tesla_smart_charger import constants, logger, security, telemetry_cache
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.models import VehicleConfig
from tesla_smart_charger.tesla_api import TeslaAPI

tsc_logger = logger.get_logger()

router = APIRouter(
    prefix="/api/v1/vehicles",
    tags=["commands"],
    dependencies=[Depends(security.require_auth)],
)

_app_config: AppConfig | None = None


def init(app_config: AppConfig) -> None:
    """Inject the shared AppConfig instance used by this router."""
    global _app_config
    _app_config = app_config


class ChargeLimitBody(BaseModel):
    """Body for setting a vehicle's target state of charge."""

    percent: int = Field(
        ge=constants.TESLA_CHARGE_LIMIT_MIN,
        le=constants.TESLA_CHARGE_LIMIT_MAX,
    )


def _require_vehicle(vehicle_id: str) -> VehicleConfig:
    """Return the configured vehicle, or raise 503/404."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    for v in _app_config.vehicles:
        if v.id == vehicle_id:
            return v
    raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")


@router.post("/{vehicle_id}/wake")
def wake_vehicle(vehicle_id: str) -> JSONResponse:
    """
    Ask Tesla to wake a vehicle.

    Returns as soon as Tesla accepts the request — the car takes a few more
    seconds to actually come online.
    """
    vehicle = _require_vehicle(vehicle_id)
    data = TeslaAPI(vehicle).wake_up()
    telemetry_cache.invalidate(vehicle.id)
    return JSONResponse(
        {"message": "Wake requested", "state": data.get("state")},
        status_code=202,
    )


@router.post("/{vehicle_id}/charge-limit")
def set_charge_limit(vehicle_id: str, body: ChargeLimitBody) -> JSONResponse:
    """Set a vehicle's target state of charge."""
    vehicle = _require_vehicle(vehicle_id)
    TeslaAPI(vehicle).set_charge_limit(body.percent)
    telemetry_cache.invalidate(vehicle.id)
    return JSONResponse(
        {"message": f"Charge limit set to {body.percent}%", "percent": body.percent},
        status_code=200,
    )


@router.post("/{vehicle_id}/refresh")
def refresh_vehicle(vehicle_id: str) -> JSONResponse:
    """
    Force a telemetry refetch for a vehicle.

    Non-blocking: drops the cached entry and starts a background fetch, so
    fresh data arrives on a subsequent poll rather than in this response.
    """
    vehicle = _require_vehicle(vehicle_id)
    telemetry_cache.invalidate(vehicle.id)
    telemetry_cache.schedule_refresh(vehicle)
    return JSONResponse(
        {"message": "Refresh scheduled", "refreshing": True},
        status_code=202,
    )
