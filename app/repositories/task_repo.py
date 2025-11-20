from sqlalchemy.orm import Session
from sqlalchemy import select, cast, String
from app.db.models import Task
from uuid import UUID

def create_task(db: Session, user_id: UUID, description: str) -> Task:
    t = Task(user_id=user_id, task_description=description)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

def get_task_owned(db: Session, user_id: UUID, task_id: UUID) -> Task | None:
    res = db.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    return res.scalar_one_or_none()

def list_tasks(db: Session, user_id: UUID, status: str | None, limit: int = 20):
    stmt = select(Task).where(Task.user_id == user_id)
    if status:
        # Use explicit casting to handle potential type mismatches
        stmt = stmt.where(cast(Task.status, String) == cast(status, String))
    stmt = stmt.order_by(Task.created_at.desc()).limit(limit)
    res = db.execute(stmt)
    return list(res.scalars())
