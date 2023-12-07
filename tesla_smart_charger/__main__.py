"""
Tesla smart car charger

This script is the main entry point for the Tesla smart car charger.
"""

import atexit
import threading
import uvicorn


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import tesla_smart_charger.constants as constants
from tesla_smart_charger.charger_config import ChargerConfig
from tesla_smart_charger.tesla_api import TeslaAPI
from tesla_smart_charger.token_cron import start_cron_job
from tesla_smart_charger.handlers.overload_handler import handle_overload


class Config(BaseModel):
    """Config class for Tesla Smart Charger."""

    maxPower: float
    minPower: float
    downStep: float
    upStep: float
    sleepTime: int
    vehicleId: str
    accessToken: str
    refreshToken: str


# Create the FastAPI app
app = FastAPI()

# Create the charger config object
tesla_config = ChargerConfig(constants.CONFIG_FILE)
tesla_config.load_config()

# Create the Tesla API object
tesla_api = TeslaAPI(tesla_config)

# Create an event to signal the cron job to stop
stop_event = threading.Event()


# Register the startup and shutdown events
async def startup_event():
    print("FastAPI application starting up")

    # Start the token refresh cron job in a separate thread
    cron_thread = threading.Thread(
        target=start_cron_job, args=(stop_event,), name="tsc_token_cron_thread"
    )
    cron_thread.start()


async def shutdown_event():
    print("FastAPI application shutting down")

    # Stop the token refresh cron job
    for thread in threading.enumerate():
        if thread.name == "tsc_token_cron_thread":
            # Set the event to signal the thread to stop
            stop_event.set()
            # Wait for the thread to finish
            thread.join()


def exit_handler():
    print("Exiting application")
    # Perform cleanup or final tasks here


# Register the exit_handler to run when the application exits
atexit.register(exit_handler)

app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


@app.get("/")
def read_root():
    return {"Hello": "World"}


# Total consumption of the house exceeds the power limit
@app.get("/overload")
def overload():
    vehicle_data = tesla_api.get_vehicle_data()
    # print(vehicle_data)

    if vehicle_data is None:
        raise HTTPException(status_code=500, detail="No vehicle data found")

    if "error" in vehicle_data:
        raise HTTPException(status_code=500, detail=vehicle_data["error"])

    if (
        vehicle_data["state"] == "online"
        and vehicle_data["charge_state"]["charging_state"] == "Charging"
    ):
        # Get the current charge limit
        charger_actual_current = vehicle_data["charge_state"]["charger_actual_current"]

        # Calculate the new charge limit
        new_charge_limit = int(charger_actual_current) * float(
            tesla_config.config["downStep"]
        )

        # Set the new charge limit
        response = tesla_api.set_charge_amp_limit(int(new_charge_limit))

        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
        else:
            # Start the overload handler in a separate thread
            overload_thread = threading.Thread(
                target=handle_overload,
                name="tsc_handle_overload_thread",
            )
            overload_thread.start()

        return response


# Total consumption of the house is below the power limit
@app.post("/underload")
def underload():
    return {"status": "ok"}


# Get the current configuration
@app.get("/config")
def get_config():
    response = tesla_config.get_config()

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return response


@app.post("/config")
def set_config(config: Config):
    response = tesla_config.set_config(config.model_dump_json())

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return response


def main():
    # Start the FastAPI server
    uvicorn.run(app=app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
