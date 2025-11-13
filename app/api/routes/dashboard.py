from fastapi import APIRouter, Depends
from sqlalchemy import select, cast, String
from app.api.deps import Authed
from app.db.models import Task, InterventionSession
from app.repositories.intervention_repo import get_recent_sessions, get_pending_checkin

router = APIRouter(prefix="/api/user", tags=["user"])

@router.get("/dashboard")
async def dashboard(ctx=Depends(Authed)):
    db = ctx["db"]; uid = ctx["user_id"]
    # Use explicit casting to handle potential type mismatches
    res = await db.execute(select(Task).where(Task.user_id==uid, cast(Task.status, String)=="active").order_by(Task.created_at.desc()).limit(10))
    active = [{"task_id": t.id, "task_description": t.task_description, "created_at": t.created_at, "status": t.status, "last_worked_on": t.last_worked_on} for t in res.scalars()]
    sessions = await get_recent_sessions(db, uid, 5)
    recent = [{"session_id": s.id, "task_description": s.task.task_description, "created_at": s.created_at, "technique_id": s.technique_id} for s in sessions]
    pending = None
    # Note: in a real DB you’d compare timestamps to now(); here we simply return the soonest with no checkin logged.
    if sessions:
        p = await get_pending_checkin(db, uid)
        if p:
            pending = {"session_id": p.id, "task_description": p.task.task_description, "scheduled_at": p.scheduled_checkin_at}
    return {"active_tasks": active, "recent_sessions": recent, "pending_checkin": pending}
