from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class TaskCreate(BaseModel):
    task_description: str

class TaskOut(BaseModel):
    task_id: UUID = Field(alias="id")
    task_description: str
    created_at: datetime
    last_worked_on: datetime | None = None
    status: str

class TaskList(BaseModel):
    tasks: list[TaskOut]
