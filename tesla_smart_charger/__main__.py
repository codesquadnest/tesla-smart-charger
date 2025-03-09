"""
Tesla Smart Car Charger.

This script is the main entry point for the Tesla smart car charger.
"""

import argparse
import asyncio
import atexit
import sys
import threading

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tesla_smart_charger import constants, utils, logger
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.controllers import db_controller
from tesla_smart_charger.cron.em_cron import start_cron_monitor
from tesla_smart_charger.cron.token_cron import start_cron_token
from tesla_smart_charger.handlers.overload_handler import handle_overload
from tesla_smart_charger.tesla_api import TeslaAPI


class Config(BaseModel):
    """Config class for Tesla Smart Charger."""

    homeMaxAmps: float
    chargerMaxAmps: float
    chargerMinAmps: float
    downStepPercentage: float
    upStepPercentage: float
    sleepTimeSecs: int
    energyMonitorIp: str
    energyMonitorType: str
    teslaVehicleId: str
    teslaAccessToken: str
    teslaRefreshToken: str
    teslaHttpProxy: str
    teslaClientId: str


# Set up tsm_logger
tsm_logger = logger.get_logger()

# Create the FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create the charger config object
tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()

# Create the Tesla API object
tesla_api = TeslaAPI(tesla_config)

# Create an event to signal the cron job to stop
stop_event = threading.Event()


def _get_thread_by_name(thread_name: str) -> threading.Thread:
    """Retrieve a thread by its name."""
    for thread in threading.enumerate():
        if thread.name == thread_name:
            return thread
    return None


def _start_cron_job(
    target_job: callable, stop_event: threading.Event, name: str
) -> None:
    """Start a new cron thread with the provided name."""
    cron_thread = threading.Thread(
        target=target_job,
        args=(stop_event,),
        name=name,
    )
    cron_thread.start()


def _init_db(type: str) -> None:
    """Initialize the database."""
    constants.DB_TYPE = type
    try:
        controller_db = db_controller.create_database_controller(
            type, constants.DB_NAME, constants.DB_FILE_PATH
        )
        controller_db.initialize_db()
        controller_db.close_connection()
        tsm_logger.info(f"Database initialized with type: {type}")
    except Exception as e:
        tsm_logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


# Register the startup and shutdown events
async def startup_event() -> None:
    """Startup event handler."""
    tsm_logger.info("FastAPI application starting up")
    _start_cron_job(start_cron_token, stop_event, "tsc_token_cron_thread")


async def shutdown_event() -> None:
    """Shutdown event handler."""
    tsm_logger.info("FastAPI application shutting down")

    # Signal the cron jobs to stop
    stop_event.set()

    # Wait for the cron jobs to stop
    for thread in threading.enumerate():
        if thread.name in ["tsc_energy_monitor_thread", "tsc_token_cron_thread"]:
            thread.join()
            tsm_logger.info(f"{thread.name} stopped")

    await asyncio.sleep(2)


def exit_handler() -> None:
    """Exit handler."""
    tsm_logger.info("Performing cleanup tasks before exit")


# Register the exit_handler to run when the application exits
atexit.register(exit_handler)

# Add event handlers to the FastAPI app
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


@app.get("/")
def read_root() -> JSONResponse:
    """Root endpoint."""
    response = {"msg": "Tesla Smart Charger API"}
    return JSONResponse(content=response, status_code=200)


@app.get("/overload")
def overload() -> JSONResponse:
    """
    Overload endpoint.

    This endpoint is called when the total consumption of the house exceeds the power
    limit.
    """
    # If a thread handler already exists, no other will be started
    if _get_thread_by_name("tsc_handle_overload_thread"):
        response = {"msg": "overload handling session already started"}
        return JSONResponse(content=response, status_code=202)
    # Load the configuration to get new token if needed
    tesla_config.load_config()
    try:
        vehicle_data = tesla_api.get_vehicle_data()
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {e!s}") from e

    if (
        vehicle_data["state"] == "online"
        and vehicle_data["charge_state"]["charging_state"] == "Charging"
    ):
        # Get the current charge limit
        charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]

        # Calculate the new charge limit
        new_charge_limit = round(float(charger_actual_current)) * float(
            tesla_config.config["downStepPercentage"],
        )

        try:
            # Set the new charge limit
            response = tesla_api.set_charge_amp_limit(round(float(new_charge_limit)))
        except HTTPException as e:
            return {"error": f"Set charge limit failed: {e!s}"}

        # Start the overload handler in a separate thread
        overload_thread = threading.Thread(
            target=handle_overload,
            name="tsc_handle_overload_thread",
        )
        overload_thread.start()

        response = {"msg": "overload handler session started"}
        return JSONResponse(content=response, status_code=200)

    response = {"msg": "overload handling not required"}
    return JSONResponse(content=response, status_code=202)


@app.post("/underload")
def underload() -> JSONResponse:
    """Underload endpoint."""
    response = {"msg": "underload session not implemented"}
    return JSONResponse(content=response, status_code=404)


@app.get("/config")
def get_config() -> JSONResponse:
    """Get the current configuration."""
    tesla_config.load_config()
    response = tesla_config.get_config()

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return JSONResponse(content=response, status_code=200)


@app.post("/config")
def set_config(config: Config) -> JSONResponse:
    """Set the configuration."""
    try:
        tesla_config.set_config(config.model_dump_json())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set config: {e!s}")
    response = tesla_config.get_config()
    return JSONResponse(content=response, status_code=200)


@app.get("/history/{num_records}")
def get_history(num_records: int) -> JSONResponse:
    """Get the history of the charger."""
    controller_db = None
    try:
        controller_db = db_controller.create_database_controller(
            constants.DB_TYPE, constants.DB_NAME, constants.DB_FILE_PATH
        )
        controller_db.initialize_db()
        data = controller_db.get_data(num_records)
        response = {"data": data}
        return JSONResponse(content=response, status_code=200)
    except Exception as e:
        tsm_logger.error(f"Failed to initialize database: {e}")
        raise HTTPException(
            status_code=500, detail="Database connection not initialized"
        ) from e
    finally:
        if controller_db:
            controller_db.close_connection()


def main() -> None:
    """Entry point for the Tesla smart charger."""
    # Parse the command line arguments
    parser = argparse.ArgumentParser(
        description="Tesla smart charger",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database",
        default="sqlite",
        help="The type of database to use",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=8000,
        type=int,
        help="The port to run the FastAPI server on",
    )
    parser.add_argument(
        "-m",
        "--monitor",
        action="store_true",
        help="Monitor the energy consumption of the house",
    )
    parser.add_argument(
        "vehicles",
        help="Get the list of vehicles from the Tesla API",
        nargs="?",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=constants.VERBOSE,
        help="Enable verbose mode",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Configure verbose mode
    if args.verbose:
        # tsm_logger.getLogger().setLevel(tsm_logger.DEBUG)
        constants.VERBOSE = True

    if args.vehicles:
        # Get the vehicles from the Tesla API
        try:
            vehicles = tesla_api.get_vehicles()
        except HTTPException as e:
            tsm_logger.error(f"Request failed: {str(e)}")
            sys.exit(1)
        utils.show_vehicles(vehicles)
        sys.exit(0)

    # Initialize the database
    _init_db(args.database)

    if args.monitor:
        # Monitor the energy consumption of the house
        _start_cron_job(start_cron_monitor, stop_event, "tsc_energy_monitor_thread")

    # Start the FastAPI server
    uvicorn.run(app=app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
