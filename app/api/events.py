from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from app.dependencies import get_db, get_current_user
from app.models import Event, User, EventStatus, Trigger
from app.schemas import EventResponse
import redis
import os
import json
from app.database import SessionLocal

router = APIRouter()

# Initialize Redis client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


@router.get(
    "/recent",
    response_model=List[EventResponse],
    dependencies=[Depends(get_current_user)],
    summary="Get Recent Events",
    description="""
    Get events from the last 2 hours (active events).

    These events are:
    * Less than 2 hours old
    * In "active" status
    * Cached for better performance

    The response includes:
    * Event ID and trigger ID
    * Timestamp when triggered
    * Payload (for API triggers)
    * Test status
    """

)
async def get_recent_events(
        show_test: bool = Query(
            False,
            description="Include test events in the results"
        ),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Try to get from cache first
    cache_key = f"recent_events:{current_user.id}:{show_test}:{page}:{page_size}"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        return json.loads(cached_data)

    # Calculate time threshold
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)

    # Build query
    query = db.query(Event).join(Trigger).filter(
        and_(
            Event.triggered_at >= two_hours_ago,
            Event.status == EventStatus.ACTIVE,
            Trigger.user_id == current_user.id
        )
    )

    if not show_test:
        query = query.filter(Event.is_test == False)

    # Apply pagination
    offset = (page - 1) * page_size
    events = query.order_by(Event.triggered_at.desc()) \
        .offset(offset) \
        .limit(page_size) \
        .all()

    # Prepare response
    result = [
        {
            "id": event.id,
            "trigger_id": event.trigger_id,
            "status": event.status,
            "payload": event.payload,
            "is_test": event.is_test,
            "triggered_at": event.triggered_at,
            "archived_at": event.archived_at,
            "deleted_at": event.deleted_at
        }
        for event in events
    ]

    # Cache for 1 minute
    redis_client.setex(
        cache_key,
        60,  # 1 minute
        json.dumps(result, default=str)
    )

    return result


@router.get(
    "/archived",
    response_model=List[EventResponse],
    summary="Get Archived Events",
    description="""
    Get archived events (2-48 hours old).

    These events are:
    * Between 2 and 48 hours old
    * In "archived" status
    * Not cached (direct database query)

    Events older than 48 hours are automatically deleted.
    """
)
async def get_archived_events(
        show_test: bool = Query(
            False,
            description="Include test events in the results"
        ),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Calculate time thresholds
    now = datetime.utcnow()
    two_hours_ago = now - timedelta(hours=2)
    forty_eight_hours_ago = now - timedelta(hours=48)

    # Build query
    query = db.query(Event).join(Trigger).filter(
        and_(
            Event.triggered_at.between(forty_eight_hours_ago, two_hours_ago),
            Event.status == EventStatus.ARCHIVED,
            Trigger.user_id == current_user.id
        )
    )

    if not show_test:
        query = query.filter(Event.is_test == False)

    # Apply pagination
    offset = (page - 1) * page_size
    events = query.order_by(Event.triggered_at.desc()) \
        .offset(offset) \
        .limit(page_size) \
        .all()

    return events


@router.post("/cleanup")
async def cleanup_events(
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Trigger manual cleanup of events.
    Archives events older than 2 hours and deletes events older than 48 hours.
    This is also done automatically on a schedule.
    """
    background_tasks.add_task(cleanup_old_events)
    return {"message": "Cleanup task scheduled"}


async def cleanup_old_events():
    """Background task to cleanup events"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        two_hours_ago = now - timedelta(hours=2)
        forty_eight_hours_ago = now - timedelta(hours=48)

        # Archive events older than 2 hours
        archive_query = db.query(Event).filter(
            and_(
                Event.triggered_at <= two_hours_ago,
                Event.status == EventStatus.ACTIVE
            )
        )

        for event in archive_query.all():
            event.status = EventStatus.ARCHIVED
            event.archived_at = now

        # Delete events older than 48 hours
        delete_query = db.query(Event).filter(
            and_(
                Event.triggered_at <= forty_eight_hours_ago,
                Event.status == EventStatus.ARCHIVED
            )
        )

        for event in delete_query.all():
            event.status = EventStatus.DELETED
            event.deleted_at = now

        db.commit()

        # Clear affected caches
        clear_event_caches()

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def clear_event_caches():
    """Clear all event-related caches"""
    for key in redis_client.scan_iter("recent_events:*"):
        redis_client.delete(key)


# Schedule periodic cleanup
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_events, 'interval', minutes=30)  # Run every 30 minutes
scheduler.start()