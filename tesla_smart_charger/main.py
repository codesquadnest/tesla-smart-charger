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
from tesla_smart_charger.token_cron import start_cron_job


class Config(BaseModel):
    """Config class for Tesla Smart Charger."""

    maxPower: float
    minPower: float
    downStep: float
    upStep: float
    teslaToken: str


# Create the FastAPI app
app = FastAPI()


# Register the startup and shutdown events
async def startup_event():
    print("FastAPI application starting up")

    # Start the token refresh cron job in a separate thread
    cron_thread = threading.Thread(
        target=start_cron_job, args=(stop_event,), name="token_cron_thread"
    )
    cron_thread.start()


async def shutdown_event():
    print("FastAPI application shutting down")

    # Stop the token refresh cron job
    for thread in threading.enumerate():
        if thread.name == "token_cron_thread":
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
@app.post("/overload")
def overload():
    return {"status": "ok"}


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


if __name__ == "__main__":
    # Create the charger config object
    tesla_config = ChargerConfig(constants.CONFIG_FILE)
    tesla_config.load_config()

    # Create an event to signal the cron job to stop
    stop_event = threading.Event()

    # Start the FastAPI server
    uvicorn.run(app, host="127.0.0.1", port=8000)
