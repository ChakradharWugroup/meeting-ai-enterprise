from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import datetime
import enum
from pgvector.sqlalchemy import Vector
from .postgres import Base

class MeetingStatus(enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED)
    summary = Column(Text, nullable=True)

    transcripts = relationship("Transcript", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("meetings.id"))
    speaker = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False) # e.g. seconds from start
    
    # 384 is standard for 'all-MiniLM-L6-v2' local embeddings
    embedding = Column(Vector(384), nullable=True)

    meeting = relationship("Meeting", back_populates="transcripts")

class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("meetings.id"))
    description = Column(Text, nullable=False)
    owner = Column(String, nullable=True)
    status = Column(String, default="open") # open, completed, canceled

    meeting = relationship("Meeting", back_populates="action_items")
