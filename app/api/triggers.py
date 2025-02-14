from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import Query, Body

from app.database import SessionLocal
from app.dependencies import get_db, get_current_user
from app.models import Trigger, User, Event, TriggerType, EventStatus
from app.schemas import (
    ScheduledTriggerCreate,
    APITriggerCreate,
    TriggerResponse,
    EventCreate
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

router = APIRouter()
scheduler = BackgroundScheduler()
scheduler.start()


@router.post(
    "/scheduled",
    response_model=TriggerResponse,
    summary="Create a Scheduled Trigger"
)
async def create_scheduled_trigger(
        trigger: ScheduledTriggerCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db_trigger = Trigger(
        name=trigger.name,
        type=TriggerType.SCHEDULED,
        schedule=trigger.schedule,
        user_id=current_user.id
    )
    db.add(db_trigger)
    db.commit()
    db.refresh(db_trigger)

    # Schedule the trigger
    try:
        if trigger.schedule.isdigit():  # Interval in minutes
            interval_minutes = int(trigger.schedule)
            scheduler.add_job(
                execute_trigger,
                'interval',
                minutes=interval_minutes,
                args=[db_trigger.id],
                id=f"trigger_{db_trigger.id}",
                replace_existing=True
            )
        else:  # Cron expression
            scheduler.add_job(
                execute_trigger,
                'cron',
                args=[db_trigger.id],
                id=f"trigger_{db_trigger.id}",
                replace_existing=True,
                **parse_cron(trigger.schedule)
            )
    except ValueError as e:
        db.delete(db_trigger)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule format: {str(e)}"
        )

    return db_trigger


@router.post(
    "/api",
    response_model=TriggerResponse,
    summary="Create an API Trigger"
)
async def create_api_trigger(
        trigger: APITriggerCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Validate schema types
    valid_types = {"str", "int", "float", "bool"}
    for field, type_name in trigger.api_schema.items():
        if type_name not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type '{type_name}' for field '{field}'. Must be one of: {valid_types}"
            )

    db_trigger = Trigger(
        name=trigger.name,
        type=TriggerType.API,
        api_schema=trigger.api_schema,
        user_id=current_user.id
    )
    db.add(db_trigger)
    db.commit()
    db.refresh(db_trigger)
    return db_trigger


@router.post(
    "/{trigger_id}/test",
    summary="Test a Trigger"
)
async def test_trigger(
        trigger_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        payload: Dict[str, Any] = Body(default=None)
):
    trigger = db.query(Trigger).filter(
        Trigger.id == trigger_id,
        Trigger.user_id == current_user.id
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    if trigger.type == TriggerType.API and payload:
        # Validate payload against schema
        try:
            validate_payload(payload, trigger.api_schema)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Create test event
    event = Event(
        trigger_id=trigger.id,
        payload=payload,
        is_test=True,
        status=EventStatus.ACTIVE
    )
    db.add(event)
    db.commit()

    return {"message": "Test trigger executed successfully", "event_id": event.id}


@router.get(
    "/",
    response_model=List[TriggerResponse],
    summary="List All Triggers"
)
async def get_triggers(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    triggers = db.query(Trigger).filter(Trigger.user_id == current_user.id).all()
    return triggers


@router.delete(
    "/{trigger_id}",
    summary="Delete a Trigger"
)
async def delete_trigger(
        trigger_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    trigger = db.query(Trigger).filter(
        Trigger.id == trigger_id,
        Trigger.user_id == current_user.id
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Remove scheduled job if it exists
    if trigger.type == TriggerType.SCHEDULED:
        try:
            scheduler.remove_job(f"trigger_{trigger_id}")
        except:
            pass  # Job might not exist

    db.delete(trigger)
    db.commit()
    return {"message": "Trigger deleted successfully"}


def parse_cron(schedule: str) -> dict:
    """Parse cron expression into kwargs for APScheduler"""
    try:
        parts = schedule.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 parts")

        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4]
        }
    except Exception as e:
        raise ValueError(f"Invalid cron expression: {str(e)}")


def validate_payload(payload: Dict[str, Any], schema: Dict[str, str]):
    """Validate payload against schema"""
    type_map = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool
    }

    for field, expected_type in schema.items():
        if field not in payload:
            raise ValueError(f"Missing required field: {field}")

        value = payload[field]
        expected_python_type = type_map[expected_type]

        if not isinstance(value, expected_python_type):
            raise ValueError(
                f"Invalid type for field '{field}'. Expected {expected_type}, got {type(value).__name__}"
            )


def execute_trigger(trigger_id: int):
    """Execute a scheduled trigger"""
    # Create a new database session for this background task
    db = SessionLocal()
    try:
        trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            return

        event = Event(
            trigger_id=trigger.id,
            status=EventStatus.ACTIVE
        )
        db.add(event)
        db.commit()
    finally:
        db.close()