from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime

class InterventionCreate(BaseModel):
    task_id: UUID
    physical_sensation: str
    internal_narrative: str
    emotion_label: str

class InterventionOut(BaseModel):
    session_id: UUID = Field(alias="id")
    ai_identified_pattern: str
    technique_id: str
    personalized_message: str
    intervention_duration_seconds: int

class StartSessionIn(BaseModel):
    started_at: datetime

class StartSessionOut(BaseModel):
    success: bool
    scheduled_checkin_at: datetime

class CheckinTimePatchIn(BaseModel):
    checkin_minutes: int
    @field_validator("checkin_minutes")
    @classmethod
    def _bounds(cls, v):
        if v < 15 or v > 120:
            raise ValueError("checkin_minutes must be between 15 and 120")
        return v

class InterventionDetailOut(BaseModel):
    session_id: UUID
    task: dict
    physical_sensation: str | None = None
    internal_narrative: str | None = None
    emotion_label: str | None = None
    technique_id: str | None = None
    personalized_message: str | None = None
    created_at: datetime
    scheduled_checkin_at: datetime | None = None
    checkin: dict | None = None

class EmotionLabelsIn(BaseModel):
    task_description: str
    physical_sensation: str
    internal_narrative: str

class EmotionLabelsOut(BaseModel):
    emotion_options: list[str]
