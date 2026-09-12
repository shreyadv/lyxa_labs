from typing import List

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware

from . import logic
from .database import CAPACITY_WATTS, get_connection, init_db
from .models import ActionResult, ApplianceCreate, ApplianceOut, EventOut, StatusOut

app = FastAPI(title="Inverter Load Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


def _status_payload(conn):
    appliances = logic.get_all_appliances(conn)
    load = logic.get_current_load(conn)
    return {
        "appliances": appliances,
        "current_load": load,
        "capacity": CAPACITY_WATTS,
        "remaining_capacity": CAPACITY_WATTS - load,
    }


@app.get("/status", response_model=StatusOut)
def get_status():
    conn = get_connection()
    try:
        return _status_payload(conn)
    finally:
        conn.close()


@app.get("/appliances", response_model=List[ApplianceOut])
def list_appliances():
    conn = get_connection()
    try:
        return logic.get_all_appliances(conn)
    finally:
        conn.close()


@app.post("/appliances", response_model=ApplianceOut, status_code=201)
def create_appliance(payload: ApplianceCreate):
    conn = get_connection()
    try:
        appliance_id = logic.register_appliance(conn, payload.name, payload.wattage, payload.priority)
        row = conn.execute("SELECT * FROM appliances WHERE id = ?", (appliance_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.delete("/appliances/{appliance_id}", response_model=ActionResult)
def remove_appliance(appliance_id: int = Path(...)):
    conn = get_connection()
    try:
        ok, result = logic.delete_appliance(conn, appliance_id)
        if not ok:
            raise HTTPException(status_code=404, detail=result)
        restored = result if isinstance(result, list) else []
        payload = _status_payload(conn)
        message = "Appliance deleted"
        if restored:
            message += f" -- restored: {', '.join(restored)}"
        return ActionResult(
            success=True,
            message=message,
            restored=restored,
            appliances=payload["appliances"],
            current_load=payload["current_load"],
            remaining_capacity=payload["remaining_capacity"],
        )
    finally:
        conn.close()


@app.post("/appliances/{appliance_id}/on", response_model=ActionResult)
def turn_on_appliance(appliance_id: int = Path(...)):
    conn = get_connection()
    try:
        success, message, shed, restored = logic.turn_on(conn, appliance_id)
        payload = _status_payload(conn)
        result = ActionResult(
            success=success,
            message=message,
            shed=shed,
            restored=restored,
            appliances=payload["appliances"],
            current_load=payload["current_load"],
            remaining_capacity=payload["remaining_capacity"],
        )
        if not success:
            raise HTTPException(status_code=409, detail=result.dict())
        return result
    finally:
        conn.close()


@app.post("/appliances/{appliance_id}/off", response_model=ActionResult)
def turn_off_appliance(appliance_id: int = Path(...)):
    conn = get_connection()
    try:
        success, message, restored = logic.turn_off(conn, appliance_id)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        payload = _status_payload(conn)
        return ActionResult(
            success=success,
            message=message,
            restored=restored,
            appliances=payload["appliances"],
            current_load=payload["current_load"],
            remaining_capacity=payload["remaining_capacity"],
        )
    finally:
        conn.close()


@app.get("/events", response_model=List[EventOut])
def get_events(limit: int = Query(50, ge=1, le=500)):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM event_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()