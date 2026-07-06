"""Token refresh cron — refreshes OAuth tokens for every configured vehicle."""

import threading

from tesla_smart_charger import logger
from tesla_smart_charger.app_config import AppConfig
from tesla_smart_charger.tesla_api import TeslaAPI

tsc_logger = logger.get_logger()

REFRESH_OK_INTERVAL = 10800   # 3 hours
REFRESH_FAIL_INTERVAL = 300   # 5 minutes


def refresh_all_tokens(app_config: AppConfig) -> bool:
    """
    Refresh OAuth tokens for every configured vehicle.

    Returns True if *all* vehicles refreshed successfully.
    """
    vehicles = app_config.vehicles
    if not vehicles:
        tsc_logger.warning("No vehicles configured; nothing to refresh.")
        return True

    region = app_config.system.region.value
    all_ok = True

    for vehicle in vehicles:
        if not vehicle.enabled:
            continue
        if not vehicle.teslaClientId:
            tsc_logger.warning(
                "Vehicle %s (%s) has no teslaClientId — skipping.",
                vehicle.id,
                vehicle.name,
            )
            continue
        if not vehicle.teslaRefreshToken:
            tsc_logger.warning(
                "Vehicle %s (%s) has no teslaRefreshToken — skipping.",
                vehicle.id,
                vehicle.name,
            )
            continue

        api = TeslaAPI(vehicle)
        result = api.refresh_token(region=region)
        if result is None:
            tsc_logger.error(
                "Token refresh FAILED for vehicle %s (%s).", vehicle.id, vehicle.name
            )
            all_ok = False
        else:
            access, refresh = result
            app_config.update_vehicle_tokens(vehicle.id, access, refresh)
            tsc_logger.info(
                "Token refreshed for vehicle %s (%s).", vehicle.id, vehicle.name
            )

    return all_ok


def start_cron_token(stop_event: threading.Event, app_config: AppConfig) -> None:
    """Cron thread: keeps all vehicle OAuth tokens fresh."""
    sleep_tick = 2
    tsc_logger.info("Token refresh cron started.")

    try:
        success = refresh_all_tokens(app_config)
    except Exception as exc:
        tsc_logger.error("Initial token refresh failed unexpectedly: %s", exc)
        success = False

    interval = REFRESH_OK_INTERVAL if success else REFRESH_FAIL_INTERVAL
    countdown = interval

    while not stop_event.is_set():
        if countdown <= 0:
            try:
                success = refresh_all_tokens(app_config)
                interval = REFRESH_OK_INTERVAL if success else REFRESH_FAIL_INTERVAL
                tsc_logger.info(
                    "Next token refresh in %ds (%s).",
                    interval,
                    "success" if success else "previous failure",
                )
            except Exception as exc:
                tsc_logger.error("Unhandled error in token refresh: %s", exc)
                interval = REFRESH_FAIL_INTERVAL
            countdown = interval
        stop_event.wait(sleep_tick)
        countdown -= sleep_tick

    tsc_logger.info("Token refresh cron stopped.")
