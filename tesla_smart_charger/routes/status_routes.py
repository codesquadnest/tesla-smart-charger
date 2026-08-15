"""GET /api/v1/status — overall system health and live state."""

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tesla_smart_charger import logger, security, telemetry_cache
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.cron import em_cron
from tesla_smart_charger.handlers import solar_handler
from tesla_smart_charger.models import SystemStatus

tsc_logger = logger.get_logger()

router = APIRouter(prefix="/api/v1", tags=["status"])

# References injected by __main__
_app_config: AppConfig | None = None
_monitor_active: bool = False
_overload_active_fn: Callable[[], bool] | None = None


def init(
    app_config: AppConfig,
    monitor_active_fn: Callable[[], bool],
    overload_active_fn: Callable[[], bool],
) -> None:
    """Inject the shared AppConfig and state-check callbacks used by this router."""
    global _app_config, _monitor_active, _overload_active_fn
    _app_config = app_config
    _monitor_active = monitor_active_fn
    _overload_active_fn = overload_active_fn


@router.get("/status", response_model=SystemStatus)
def get_status() -> JSONResponse:
    """Return overall system status including live vehicle states."""
    if _app_config is None:
        return JSONResponse({"error": "Not initialised"}, status_code=503)

    cfg = _app_config.system
    overload_active = _overload_active_fn() if callable(_overload_active_fn) else False
    vehicle_statuses = [
        telemetry_cache.get(v, overload_active=overload_active)
        for v in _app_config.vehicles
    ]

    status = SystemStatus(
        configured=cfg.configured,
        monitorActive=_monitor_active()
        if callable(_monitor_active)
        else _monitor_active,
        overloadActive=overload_active,
        solarActive=solar_handler.is_surplus_active(),
        solarSurplusEnabled=cfg.solarSurplusEnabled,
        currentSurplusAmps=em_cron.LAST_SURPLUS_AMPS,
        authEnabled=security.auth_configured(),
        currentConsumptionAmps=em_cron.LAST_CONSUMPTION_AMPS,
        homeMaxAmps=cfg.homeMaxAmps,
        region=cfg.region.value,
        voltage=cfg.voltage,
        vehicles=vehicle_statuses,
    )
    return JSONResponse(status.model_dump(), status_code=200)
