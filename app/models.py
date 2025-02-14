# SQLAlchmey Models

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class TriggerType(str, enum.Enum):
    SCHEDULED = "scheduled"
    API = "api"

class EventStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)

class Trigger(Base):
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(Enum(TriggerType))
    schedule = Column(String, nullable=True)  # For scheduled triggers
    api_schema = Column(JSON, nullable=True)  # For API triggers
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    trigger_id = Column(Integer, ForeignKey("triggers.id"))
    status = Column(Enum(EventStatus), default=EventStatus.ACTIVE)
    payload = Column(JSON, nullable=True)
    is_test = Column(Boolean, default=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)