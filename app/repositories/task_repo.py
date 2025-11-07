from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Task
from uuid import UUID

async def create_task(db: AsyncSession, user_id: UUID, description: str) -> Task:
    t = Task(user_id=user_id, task_description=description)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t

async def get_task_owned(db: AsyncSession, user_id: UUID, task_id: UUID) -> Task | None:
    res = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    return res.scalar_one_or_none()

async def list_tasks(db: AsyncSession, user_id: UUID, status: str | None, limit: int = 20):
    stmt = select(Task).where(Task.user_id == user_id)
    if status:
        stmt = stmt.where(Task.status == status)
    stmt = stmt.order_by(Task.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars())
