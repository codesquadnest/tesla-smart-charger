"""Constants for the Tesla Smart Charger integration."""

# Path to the certificate file
TLS_CERT_PATH = "certs/tls-cert.pem"
TLS_KEY_PATH = "certs/tls-key.pem"

# Verbose mode
VERBOSE = False

# Request delay in milliseconds
REQUEST_DELAY_MS = 3000

# Maximum number of queries to the Tesla API during overload handling session
MAX_QUERIES = 5

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
    "sleepTimeSecs": "30",
    "teslaVehicleId": "",
    "teslaAccessToken": "",
    "teslaRefreshToken": "",
    "teslaHttpProxy": "",
    "teslaClientId": "",
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
    "teslaHttpProxy",
    "teslaClientId",
]

# URL for the Tesla API to get the access token
TESLA_API_TOKEN_URL = "https://auth.tesla.com/oauth2/v3/token"

# URL for Tesla audience
TESLA_AUDIENCE = "https://fleet-api.prd.eu.vn.cloud.tesla.com"

# URL for the Tesla API to get the vehicle list
TESLA_API_VEHICLES_URL = "/api/1/vehicles"

# URL for the Tesla API to get the vehicle data
TESLA_API_VEHICLE_DATA_URL = f"/api/1/vehicles/{{id}}/vehicle_data"  # noqa: F541

# URL for the Tesla API to set the charging Amperage limit
TESLA_API_CHARGE_AMP_LIMIT_URL = f"/api/1/vehicles/{{id}}/command/set_charging_amps"  # noqa: F541

# Energy Monitor Controller states
EM_CONTROLLER_STATE_IDLE = "IDLE"
EM_CONTROLLER_STATE_OVERLOAD = "OVERLOAD"
EM_CONTROLLER_STATE_UNDERLOAD = "UNDERLOAD"

# Database settings
DB_NAME = "tesla_smart_charger"
DB_FILE_PATH = "tesla_smart_charger.db"
DB_TYPE = "sqlite"
DB_HOST = "localhost"
DB_PORT = "5432"
