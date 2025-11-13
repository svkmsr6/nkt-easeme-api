from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional

class TimeStamped(BaseModel):
    created_at: datetime

class IdModel(BaseModel):
    id: UUID = Field(serialization_alias="task_id")

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None

class DatabaseError(ErrorResponse):
    error_code: str = "DATABASE_ERROR"
