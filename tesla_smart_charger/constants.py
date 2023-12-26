"""
Constants for the Tesla Smart Charger integration.
"""

# Verbose mode
VERBOSE = False

# Request delay in milliseconds
REQUEST_DELAY_MS = 3000

# Path to the configuration file
CONFIG_FILE = "config.json"

# Supported energy monitor types
SUPPORTED_EM_TYPES = ["shelly_em"]

# Default configuration
DEFAULT_CONFIG = {
    "homeMaxAmps": "30.0",
    "chargerMaxAmps": "25.0",
    "chargerMinAmps": "6.0",
    "downStepPercentage": "0.5",
    "upStepPercentage": "0.25",
    "energyMonitorIp": "",
    "energyMonitorType": "",
    "sleepTimeSecs": "300",
    "teslaVehicleId": "",
    "teslaAccessToken": "",
    "teslaRefreshToken": "",
}

# Required configuration keys
REQUIRED_CONFIG_KEYS = [
    "homeMaxAmps",
    "chargerMaxAmps",
    "chargerMinAmps",
    "downStepPercentage",
    "upStepPercentage",
    "energyMonitorIp",
    "energyMonitorType",
    "sleepTimeSecs",
    "teslaVehicleId",
    "teslaAccessToken",
    "teslaRefreshToken",
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

# Energy Monitor Controller states
EM_CONTROLLER_STATE_IDLE = "IDLE"
EM_CONTROLLER_STATE_OVERLOAD = "OVERLOAD"
EM_CONTROLLER_STATE_UNDERLOAD = "UNDERLOAD"
