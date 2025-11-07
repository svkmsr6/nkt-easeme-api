from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import Authed
from app.schemas.task import TaskCreate, TaskOut, TaskList
from app.repositories.task_repo import create_task, list_tasks
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("", response_model=TaskOut, status_code=201)
async def create(payload: TaskCreate, ctx=Depends(Authed)):
    db: AsyncSession = ctx["db"]; user_id = ctx["user_id"]
    if not payload.task_description:
        raise HTTPException(status_code=400, detail="Missing task_description")
    t = await create_task(db, user_id, payload.task_description)
    return t

@router.get("", response_model=TaskList)
async def get_tasks(status: str | None = Query(default=None, pattern="^(active|completed|abandoned)$"), limit: int = 20, ctx=Depends(Authed)):
    tasks = await list_tasks(ctx["db"], ctx["user_id"], status, limit)
    return {"tasks": tasks}
