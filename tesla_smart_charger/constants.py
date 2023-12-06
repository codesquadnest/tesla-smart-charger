"""
Constants for the Tesla Smart Charger integration.
"""

# Path to the configuration file
CONFIG_FILE = "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "maxPower": "13.0",
    "minPower": "6.0",
    "downStep": "0.5",
    "upStep": "0.25",
    "sleepTime": "300",
    "vehicleId": "1234567890",
    "accessToken": "1234567890",
    "refreshToken": "0987654321",
}

# Required configuration keys
REQUIRED_CONFIG_KEYS = [
    "maxPower",
    "minPower",
    "downStep",
    "upStep",
    "sleepTime",
    "vehicleId",
    "accessToken",
    "refreshToken",
]

# Base URL for the Tesla API
TESLA_API_BASE_URL = "https://owner-api.teslamotors.com"

# URL for the Tesla API to get the access token
TESLA_API_TOKEN_URL = "https://auth.tesla.com/oauth2/v3/token"

# URL for the Tesla API to get the vehicle list
TESLA_API_VEHICLES_URL = f"{TESLA_API_BASE_URL}/api/1/vehicles"

# URL for the Tesla API to get the vehicle data
TESLA_API_VEHICLE_DATA_URL = f"{TESLA_API_BASE_URL}/api/1/vehicles/{{id}}/vehicle_data"

# URL for the Tesla API to set the charging Amperage limit
TESLA_API_CHARGE_AMP_LIMIT_URL = f"{TESLA_API_BASE_URL}/api/1/vehicles/{{id}}/command/set_charging_amps"
