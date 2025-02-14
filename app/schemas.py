# Pydantic Schemas

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from app.models import TriggerType, EventStatus
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TriggerBase(BaseModel):
    name: str
    type: TriggerType


class ScheduledTriggerCreate(TriggerBase):
    schedule: str  # Cron expression or interval
    type: TriggerType = TriggerType.SCHEDULED


class APITriggerCreate(TriggerBase):
    api_schema: Dict[str, Any]
    type: TriggerType = TriggerType.API


class TriggerResponse(TriggerBase):
    id: int
    created_at: datetime
    schedule: Optional[str] = None
    api_schema: Optional[Dict[str, Any]] = None
    user_id: int

    class Config:
        from_attributes = True


class EventBase(BaseModel):
    trigger_id: int
    payload: Optional[Dict[str, Any]] = None
    is_test: bool = False


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: int
    status: EventStatus
    triggered_at: datetime
    archived_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True