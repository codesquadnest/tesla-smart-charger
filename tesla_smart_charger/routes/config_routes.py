"""GET /api/v1/config  and  POST /api/v1/config — system configuration."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tesla_smart_charger import logger
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.models import OverloadStrategy, TeslaRegion

tsc_logger = logger.get_logger()

router = APIRouter(prefix="/api/v1", tags=["config"])

_app_config: Optional[AppConfig] = None


def init(app_config: AppConfig) -> None:
    global _app_config
    _app_config = app_config


class SystemConfigUpdate(BaseModel):
    """Partial system config update body — all fields optional."""

    homeMaxAmps: Optional[float] = None
    voltage: Optional[float] = None
    region: Optional[TeslaRegion] = None
    energyMonitorIp: Optional[str] = None
    energyMonitorType: Optional[str] = None
    sleepTimeSecs: Optional[int] = None
    downStepPercentage: Optional[float] = None
    upStepPercentage: Optional[float] = None
    overloadStrategy: Optional[OverloadStrategy] = None
    hostIp: Optional[str] = None
    apiPort: Optional[int] = None


@router.get("/config")
def get_config() -> JSONResponse:
    """Return the current system configuration (auth credentials are redacted)."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    data = _app_config.system.model_dump()
    # Redact password hash from the response
    if "auth" in data:
        data["auth"].pop("passwordHash", None)
    return JSONResponse(data, status_code=200)


@router.post("/config")
def update_config(body: SystemConfigUpdate) -> JSONResponse:
    """Merge provided fields into the system configuration and persist."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    updates: Dict[str, Any] = {
        k: v for k, v in body.model_dump().items() if v is not None
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    try:
        new_cfg = _app_config.update_system(updates)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    data = new_cfg.model_dump()
    if "auth" in data:
        data["auth"].pop("passwordHash", None)
    return JSONResponse(data, status_code=200)
