from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import text, ForeignKey, String, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from typing import Optional, List

psychological_pattern_enum = Enum(
    "perfectionism", "overwhelm", "fear", "decision_fatigue",
    name="psychological_pattern",
    schema="public"
)

intervention_technique_enum = Enum(
    "permission_protocol", "single_next_action", "choice_elimination", "1min_entry",
    name="intervention_technique",
    schema="public"
)

outcome_enum = Enum(
    "started_kept_going", "started_stopped", "didnt_start", "still_working",
    name="checkin_outcome",
    schema="public"
)

class Base(DeclarativeBase): 
    __table_args__ = {"schema": "app"}

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_description: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    last_worked_on: Mapped[Optional[datetime]]
    status: Mapped[str] = mapped_column(String, server_default=text("'active'"))
    sessions: Mapped[List["InterventionSession"]] = relationship(back_populates="task", cascade="all, delete")

class InterventionSession(Base):
    __tablename__ = "intervention_sessions"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.tasks.id", ondelete="CASCADE"))
    task: Mapped["Task"] = relationship(back_populates="sessions")
    physical_sensation: Mapped[Optional[str]]
    internal_narrative: Mapped[Optional[str]]
    emotion_label: Mapped[Optional[str]]
    ai_identified_pattern: Mapped[Optional[str]] = mapped_column(psychological_pattern_enum)
    technique_id: Mapped[Optional[str]] = mapped_column(intervention_technique_enum)
    personalized_message: Mapped[Optional[str]]
    intervention_duration_seconds: Mapped[Optional[int]]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    intervention_started_at: Mapped[Optional[datetime]]
    scheduled_checkin_at: Mapped[Optional[datetime]]
    checkins: Mapped[List["CheckIn"]] = relationship(back_populates="session", cascade="all, delete")

class CheckIn(Base):
    __tablename__ = "checkins"
    __table_args__ = {"schema": "app"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.intervention_sessions.id", ondelete="CASCADE"))
    session: Mapped["InterventionSession"] = relationship(back_populates="checkins")
    outcome: Mapped[str]= mapped_column(outcome_enum)
    optional_notes: Mapped[Optional[str]]
    emotion_after: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
