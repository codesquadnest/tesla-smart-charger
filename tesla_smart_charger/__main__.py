"""Tesla smart car charger.

This script is the main entry point for the Tesla smart car charger.
"""

import argparse
import atexit
import sys
import threading

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tesla_smart_charger import constants, utils
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.handlers.overload_handler import handle_overload
from tesla_smart_charger.tesla_api import TeslaAPI
from tesla_smart_charger.token_cron import start_cron_job


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


# Create the FastAPI app
app = FastAPI()

# Create the charger config object
tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()

# Create the Tesla API object
tesla_api = TeslaAPI(tesla_config)

# Create an event to signal the cron job to stop
stop_event = threading.Event()


def _get_thread_by_name(thread_name: str) -> str:
    for thread in threading.enumerate():
        if thread.name == thread_name:
            return thread
    return None


# Register the startup and shutdown events
async def startup_event() -> None:
    """Startup event handler."""
    print("FastAPI application starting up")

    # Start the token refresh cron job in a separate thread
    cron_thread = threading.Thread(
        target=start_cron_job,
        args=(stop_event,),
        name="tsc_token_cron_thread",
    )
    cron_thread.start()


async def shutdown_event() -> None:
    """Shutdown event handler."""
    print("FastAPI application shutting down")

    # Stop the token refresh cron job
    stop_event.set()
    _get_thread_by_name("tsc_token_cron_thread").join()


def exit_handler() -> None:
    """Exit handler."""
    # Perform cleanup or final tasks here


# Register the exit_handler to run when the application exits
atexit.register(exit_handler)

app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


@app.get("/")
def read_root() -> JSONResponse:
    """Root endpoint."""
    response = {"msg": "Tesla Smart Charger API"}
    return JSONResponse(content=response, status_code=200)


@app.get("/overload")
def overload() -> JSONResponse:
    """Overload endpoint.

    This endpoint is called when the total consumption of the house exceeds the power
    limit.
    """
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
        new_charge_limit = int(charger_actual_current) * float(
            tesla_config.config["downStepPercentage"],
        )

        try:
            # Set the new charge limit
            response = tesla_api.set_charge_amp_limit(int(new_charge_limit))
        except HTTPException as e:
            return {"error": f"Set charge limit failed: {e!s}"}

        # If a thread handler already exists no other will be started
        if _get_thread_by_name("tsc_handle_overload_thread"):
            response = {"msg": "overload handling session already started"}
            return JSONResponse(content=response, status_code=202)

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


# Total consumption of the house is below the power limit
@app.post("/underload")
def underload() -> JSONResponse:
    """Underload endpoint."""
    response = {"msg": "underload session not implemented"}
    return JSONResponse(content=response, status_code=404)


# Get the current configuration
@app.get("/config")
def get_config() -> JSONResponse:
    """Config endpoint."""
    tesla_config.load_config()
    response = tesla_config.get_config()

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return JSONResponse(content=response, status_code=200)


@app.post("/config")
def set_config(config: Config) -> JSONResponse:
    """Config endpoint."""
    response = tesla_config.set_config(config.model_dump_json())

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return response


def main() -> None:
    """Entry point for the Tesla smart car charger."""
    # Parse the command line arguments
    parser = argparse.ArgumentParser(
        description="Tesla smart car charger",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--port",
        default=8000,
        type=int,
        help="The port to run the FastAPI server on",
    )
    # Vehicles argument to get the list of vehicles from the Tesla API
    # not required to run the FastAPI server
    parser.add_argument(
        "vehicles",
        help="Get the list of vehicles from the Tesla API",
        nargs="?",
        default=None,
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
        constants.VERBOSE = True

    if args.vehicles:
        # Get the vehicles from the Tesla API
        try:
            vehicles = tesla_api.get_vehicles()
        except HTTPException as e:
            print("Request failed:", str(e))
            sys.exit(1)
        utils.show_vehicles(vehicles)
        # Exit the application
        sys.exit(0)

    # Start the FastAPI server
    uvicorn.run(app=app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
