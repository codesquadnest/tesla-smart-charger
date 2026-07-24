"""GET /api/v1/history — paginated, filterable overload event history."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from tesla_smart_charger import constants, logger
from tesla_smart_charger.controllers import db_controller

tsc_logger = logger.get_logger()

router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history")
def get_history(
    limit: Annotated[
        int, Query(ge=1, le=500, description="Maximum records to return")
    ] = 50,
    vehicle_id: Annotated[str, Query(description="Filter by vehicle UUID")] = "",
    from_date: Annotated[
        str, Query(description="Lower bound (YYYY-MM-DD HH:MM:SS)")
    ] = "",
    to_date: Annotated[
        str, Query(description="Upper bound (YYYY-MM-DD HH:MM:SS)")
    ] = "",
) -> JSONResponse:
    """Return filtered overload event history."""
    ctrl = None
    try:
        ctrl = db_controller.create_database_controller(
            constants.DB_TYPE, constants.DB_NAME, constants.DB_FILE_PATH
        )
        ctrl.initialize_db()
        if hasattr(ctrl, "get_data_filtered"):
            data = ctrl.get_data_filtered(
                num_records=limit,
                vehicle_id=vehicle_id,
                from_date=from_date,
                to_date=to_date,
            )
        else:
            data = ctrl.get_data(limit)
        return JSONResponse({"data": data, "count": len(data)}, status_code=200)
    except Exception as exc:
        tsc_logger.exception("History query failed")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        if ctrl:
            try:
                ctrl.close_connection()
            except sqlite3.Error as exc:
                tsc_logger.debug("Error closing DB connection: %s", exc)


# Backward-compatible endpoint kept for legacy em_cron self-calls
@router.get("/history/{num_records}")
def get_history_legacy(num_records: int) -> JSONResponse:
    """Return the most recent overload event records (legacy, unfiltered)."""
    ctrl = None
    try:
        ctrl = db_controller.create_database_controller(
            constants.DB_TYPE, constants.DB_NAME, constants.DB_FILE_PATH
        )
        ctrl.initialize_db()
        data = ctrl.get_data(num_records)
        return JSONResponse({"data": data}, status_code=200)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        if ctrl:
            try:
                ctrl.close_connection()
            except sqlite3.Error as exc:
                tsc_logger.debug("Error closing DB connection: %s", exc)
