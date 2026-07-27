"""
Tesla Smart Charger — application entry point.

Wires together FastAPI routes, AppConfig, background cron threads,
and serves the React dashboard from ``dashboard/dist/``.
"""

import argparse
import asyncio
import atexit
import sys
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tesla_smart_charger import constants, logger, security, utils
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.controllers import db_controller
from tesla_smart_charger.cron import em_cron, token_cron
from tesla_smart_charger.handlers import overload_handler
from tesla_smart_charger.models import VehicleConfig
from tesla_smart_charger.routes import (
    auth_routes,
    command_routes,
    config_routes,
    history_routes,
    status_routes,
    vehicle_routes,
)
from tesla_smart_charger.tesla_api import TeslaAPI

# ─── Logging ──────────────────────────────────────────────────────────────────

tsm_logger = logger.get_logger()

# ─── Shared singleton config ──────────────────────────────────────────────────

app_config = AppConfig(constants.CONFIG_DIR)
app_config.load()

# ─── Thread helpers ────────────────────────────────────────────────────────────

stop_event = threading.Event()


def _get_thread(name: str) -> threading.Thread | None:
    for t in threading.enumerate():
        if t.name == name:
            return t
    return None


def _start_thread(target: Callable[..., None], name: str, *extra_args: object) -> None:
    t = threading.Thread(
        target=target, args=(stop_event, *extra_args), name=name, daemon=True
    )
    t.start()
    tsm_logger.info("Thread started: %s", name)


def _monitor_active() -> bool:
    return _get_thread("tsc_energy_monitor_thread") is not None


# ─── Database initialisation ───────────────────────────────────────────────────


def _init_db(db_type: str) -> None:
    constants.DB_TYPE = db_type
    try:
        ctrl = db_controller.create_database_controller(
            db_type, constants.DB_NAME, constants.DB_FILE_PATH
        )
        ctrl.initialize_db()
        ctrl.close_connection()
        tsm_logger.info("Database initialised (%s).", db_type)
    # Deliberately broad: any failure here is fatal at startup and must be
    # logged before exiting, regardless of the underlying cause.
    except Exception:
        tsm_logger.exception("Database initialisation failed")
        sys.exit(1)


# ─── FastAPI lifespan ──────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Start background cron threads on startup and join them on shutdown."""
    tsm_logger.info("Tesla Smart Charger starting up.")
    _start_thread(token_cron.start_cron_token, "tsc_token_cron_thread", app_config)
    yield
    tsm_logger.info("Tesla Smart Charger shutting down.")
    stop_event.set()
    for tname in ("tsc_energy_monitor_thread", "tsc_token_cron_thread"):
        t = _get_thread(tname)
        if t:
            t.join(timeout=10)
            tsm_logger.info("%s stopped.", tname)
    await asyncio.sleep(1)


# ─── FastAPI application ───────────────────────────────────────────────────────

app = FastAPI(title="Tesla Smart Charger", version="2.0.0", lifespan=lifespan)
# A wildcard origin ("*") is incompatible with allow_credentials=True — browsers
# reject credentialed responses that echo "*". Only enable credentials when the
# origins are explicitly listed.
_cors_origins = app_config.system.corsOrigins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Include versioned route modules ──────────────────────────────────────────

security.init(app_config)
config_routes.init(app_config)
vehicle_routes.init(app_config)
command_routes.init(app_config)
auth_routes.init(app_config)
status_routes.init(app_config, _monitor_active, overload_handler.is_session_active)

app.include_router(status_routes.router)
app.include_router(config_routes.router)
app.include_router(vehicle_routes.router)
app.include_router(command_routes.router)
app.include_router(auth_routes.router)
app.include_router(history_routes.router)

# ─── Legacy endpoints (kept for backward compatibility) ───────────────────────


@app.get("/overload")
def overload() -> JSONResponse:
    """
    Trigger an overload handling session.

    Called automatically by the energy monitor cron when consumption
    exceeds the home limit.  Can also be called manually for testing.
    """
    started, msg = overload_handler.trigger_overload(app_config)
    status_code = 200 if started else 202
    return JSONResponse({"msg": msg}, status_code=status_code)


@app.post("/underload")
def underload() -> JSONResponse:
    """Return a placeholder response for the not-yet-implemented underload endpoint."""
    return JSONResponse(
        {"msg": "underload session not yet implemented"}, status_code=501
    )


# ─── Static files — React dashboard ───────────────────────────────────────────

DASHBOARD_DIST = Path("dashboard/dist")
DASHBOARD_ASSETS = DASHBOARD_DIST / "assets"

if DASHBOARD_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(DASHBOARD_ASSETS)), name="assets")


@app.get("/")
def serve_index() -> FileResponse:
    """Serve the React SPA entry point."""
    index_path = DASHBOARD_DIST / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    legacy = Path("tesla_smart_charger/website/index.html")
    if legacy.exists():
        return FileResponse(str(legacy))
    raise HTTPException(
        status_code=503,
        detail="Dashboard not built. Run: cd dashboard && npm install && npm run build",
    )


@app.get("/{full_path:path}")
def spa_catch_all(full_path: str) -> FileResponse:
    """Catch-all for React Router client-side navigation."""
    static_file = DASHBOARD_DIST / full_path
    # Prevent path traversal: only serve files that resolve inside DASHBOARD_DIST.
    try:
        static_file.resolve().relative_to(DASHBOARD_DIST.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found") from None
    if static_file.is_file():
        return FileResponse(str(static_file))
    index_path = DASHBOARD_DIST / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Not found")


# ─── Exit handler ─────────────────────────────────────────────────────────────


def _exit_handler() -> None:
    tsm_logger.info("Exit handler: cleanup complete.")


atexit.register(_exit_handler)


# ─── CLI entry point ───────────────────────────────────────────────────────────


def _print_tesla_vehicles(vehicle: VehicleConfig) -> None:
    """Print the Tesla vehicles linked to *vehicle*'s OAuth token, or log on failure."""
    try:
        api = TeslaAPI(vehicle)
        remote = api.get_vehicles()
        utils.show_vehicles(remote)
    except Exception:
        tsm_logger.exception("Could not fetch vehicles for %s", vehicle.id)


def main() -> None:
    """Parse CLI args and either print the vehicle list or start the server."""
    parser = argparse.ArgumentParser(
        description="Tesla Smart Charger",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--database", default="sqlite", help="Database backend type")
    parser.add_argument("-p", "--port", default=8000, type=int, help="HTTP port")
    parser.add_argument(
        "-m", "--monitor", action="store_true", help="Enable energy monitor polling"
    )
    parser.add_argument(
        "vehicles",
        nargs="?",
        help="Print vehicle list from Tesla API and exit",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=constants.VERBOSE
    )

    args = parser.parse_args()

    if args.verbose:
        constants.VERBOSE = True

    if args.vehicles:
        vehicles_list = app_config.vehicles
        if not vehicles_list:
            print("No vehicles configured yet. Complete the onboarding wizard first.")
            sys.exit(0)
        for v in vehicles_list:
            _print_tesla_vehicles(v)
        sys.exit(0)

    _init_db(args.database)

    if args.monitor:
        _start_thread(
            em_cron.start_cron_monitor, "tsc_energy_monitor_thread", app_config
        )

    uvicorn.run(app=app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
