from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class CheckinCreate(BaseModel):
    session_id: UUID
    outcome: str  # started_kept_going | started_stopped | did_not_start | still_working
    optional_notes: str | None = None
    emotion_after: str | None = None

class CheckinOut(BaseModel):
    checkin_id: UUID
    created_at: datetime
    suggestion: str
