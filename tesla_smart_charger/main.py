"""
Tesla smart car charger

This script is the main entry point for the Tesla smart car charger.
"""


from fastapi import FastAPI
from pydantic import BaseModel

from tesla_smart_charger.tesla_config import TeslaConfig


class Config(BaseModel):
    """Config class for Tesla Smart Charger."""

    maxPower: float
    minPower: float
    downStep: float
    upStep: float
    teslaToken: str


tesla_config = TeslaConfig("config.json")
tesla_config.load_config()

# Create the FastAPI app
app = FastAPI()


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
async def get_config():
    return tesla_config.get_config()

@app.post("/config")
async def set_config(config: Config):
    tesla_config.set_config(config.model_dump_json())
    return tesla_config.get_config()
