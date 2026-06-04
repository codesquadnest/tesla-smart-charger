"""Constants for the Tesla Smart Charger integration."""

import os
from pathlib import Path

# Optional environment variable override
CERTS_DIR = Path(
    os.getenv("TESLA_CERTS_DIR", Path(__file__).resolve().parent.parent / "certs")
).resolve()

TLS_CERT_PATH = CERTS_DIR / "tls-cert.pem"
TLS_KEY_PATH = CERTS_DIR / "tls-key.pem"

# Verbose mode
VERBOSE = False

# Request delay in milliseconds
REQUEST_DELAY_MS = 3000

# Maximum number of queries to the Tesla API during overload handling session
MAX_QUERIES = 5

# ─── Config files ──────────────────────────────────────────────────────────────

# New structured config directory
CONFIG_DIR = "config"
SYSTEM_CONFIG_FILE = "config/system.json"
VEHICLES_CONFIG_FILE = "config/vehicles.json"

# Legacy config file (auto-migrated on first startup)
LEGACY_CONFIG_FILE = "config.json"

# Kept for backward compatibility with existing tests / ChargerConfig
CONFIG_FILE = "config.json"

# ─── Tesla API ─────────────────────────────────────────────────────────────────

# URL for the Tesla Auth API (token refresh — region-agnostic)
TESLA_API_TOKEN_URL = "https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token"

# Tesla OAuth 2.0 authorization endpoint
TESLA_AUTH_URL = "https://auth.tesla.com/oauth2/v3/authorize"

# Tesla Fleet API base URLs per region
TESLA_FLEET_API_URLS: dict[str, str] = {
    "eu": "https://fleet-api.prd.eu.vn.cloud.tesla.com",
    "na": "https://fleet-api.prd.na.vn.cloud.tesla.com",
    "ap": "https://fleet-api.prd.ap.vn.cloud.tesla.com",
}

# Default audience (EU — kept for backward compatibility)
TESLA_AUDIENCE = TESLA_FLEET_API_URLS["eu"]

# Tesla Fleet API path templates
TESLA_API_VEHICLES_URL = "/api/1/vehicles"
TESLA_API_VEHICLE_DATA_URL = "/api/1/vehicles/{id}/vehicle_data"
TESLA_API_CHARGE_AMP_LIMIT_URL = "/api/1/vehicles/{id}/command/set_charging_amps"

# Tesla OAuth scopes required by this application
TESLA_OAUTH_SCOPES = (
    "openid offline_access vehicle_device_data vehicle_cmds vehicle_charging_cmds"
)

# ─── Energy Monitor ────────────────────────────────────────────────────────────

SUPPORTED_EM_TYPES = ["shelly_em"]

EM_CONTROLLER_STATE_IDLE = "IDLE"
EM_CONTROLLER_STATE_OVERLOAD = "OVERLOAD"
EM_CONTROLLER_STATE_UNDERLOAD = "UNDERLOAD"

# ─── Database ──────────────────────────────────────────────────────────────────

DB_NAME = "tesla_smart_charger"
DB_FILE_PATH = "tesla_smart_charger.db"
DB_TYPE = "sqlite"
DB_HOST = "localhost"
DB_PORT = "5432"

# ─── Legacy config (kept for backward compatibility with ChargerConfig) ─────────

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
