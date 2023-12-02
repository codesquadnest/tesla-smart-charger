"""
Constants for the Tesla Smart Charger integration.
"""

# Path to the configuration file
CONFIG_FILE = "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "maxPower": 11.0,
    "minPower": 6.0,
    "downStep": 0.5,
    "upStep": 0.5,
    "teslaToken": "1234567890"
}

# Required configuration keys
REQUIRED_CONFIG_KEYS = ["maxPower", "minPower", "downStep", "upStep", "teslaToken"]

# Base URL for the Tesla API
TESLA_API_BASE_URL = "https://owner-api.teslamotors.com"

# URL for the Tesla API to get the vehicle list
TESLA_API_VEHICLES_URL = f"{TESLA_API_BASE_URL}/api/1/vehicles"

# URL for the Tesla API to get the vehicle data
TESLA_API_VEHICLE_DATA_URL = f"{TESLA_API_BASE_URL}/api/1/vehicles/{{id}}/vehicle_data"

# URL for the Tesla API to get the vehicle charge state
TESLA_API_VEHICLE_CHARGE_STATE_URL = (
    f"{TESLA_API_BASE_URL}/api/1/vehicles/{{id}}/data_request/charge_state"
)

# URL for the Tesla API to set the vehicle charge limit
TESLA_API_VEHICLE_CHARGE_LIMIT_URL = (
    f"{TESLA_API_BASE_URL}/api/1/vehicles/{{id}}/command/set_charge_limit"
)

# URL for the Tesla API to get the vehicle charge state
TESLA_API_VEHICLE_STATE_URL = (
    f"{TESLA_API_BASE_URL}/api/1/vehicles/{{id}}/data_request/vehicle_state"
)
