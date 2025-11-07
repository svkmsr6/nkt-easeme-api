from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class TimeStamped(BaseModel):
    created_at: datetime

class IdModel(BaseModel):
    id: UUID = Field(serialization_alias="task_id")
