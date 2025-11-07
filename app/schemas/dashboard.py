from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class DashboardOut(BaseModel):
    active_tasks: list[dict]
    recent_sessions: list[dict]
    pending_checkin: dict | None = None
