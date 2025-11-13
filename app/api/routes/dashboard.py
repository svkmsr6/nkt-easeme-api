from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, cast, String
from sqlalchemy.exc import ProgrammingError, OperationalError
from app.api.deps import Authed
from app.db.models import Task, InterventionSession
from app.repositories.intervention_repo import get_recent_sessions, get_pending_checkin
import logging

router = APIRouter(prefix="/api/user", tags=["user"])

@router.get("/dashboard")
async def dashboard(ctx=Depends(Authed)):
    logger = logging.getLogger(__name__)
    db = ctx["db"]; uid = ctx["user_id"]
    
    try:
        # Use explicit casting to handle potential type mismatches
        res = await db.execute(select(Task).where(Task.user_id==uid, cast(Task.status, String)=="active").order_by(Task.created_at.desc()).limit(10))
        active = [{"task_id": t.id, "task_description": t.task_description, "created_at": t.created_at, "status": t.status, "last_worked_on": t.last_worked_on} for t in res.scalars()]
        
        # Try to get recent sessions with fallback handling
        sessions = []
        try:
            sessions = await get_recent_sessions(db, uid, 5)
        except ProgrammingError as e:
            logger.warning(f"Schema mismatch in get_recent_sessions for user {uid}: {e}")
            # Continue without recent sessions data
            sessions = []
        except Exception as e:
            logger.error(f"Unexpected error in get_recent_sessions for user {uid}: {e}")
            # Continue without recent sessions data  
            sessions = []
        recent = [{"session_id": s.id, "task_description": s.task.task_description, "created_at": s.created_at, "technique_id": s.technique_id} for s in sessions]
        
        pending = None
        # Note: in a real DB you'd compare timestamps to now(); here we simply return the soonest with no checkin logged.
        if sessions:
            try:
                p = await get_pending_checkin(db, uid)
                if p:
                    pending = {"session_id": p.id, "task_description": p.task.task_description, "scheduled_at": p.scheduled_checkin_at}
            except Exception as e:
                logger.warning(f"Error getting pending checkin for user {uid}: {e}")
                # Continue without pending checkin data
                pass
        
        return {"active_tasks": active, "recent_sessions": recent, "pending_checkin": pending}
    
    except ProgrammingError as e:
        logger.error(f"Database programming error in dashboard for user {uid}: {e}")
        # Re-raise to let the global handler deal with it
        raise
    except OperationalError as e:
        logger.error(f"Database operational error in dashboard for user {uid}: {e}")
        # Re-raise to let the global handler deal with it
        raise
    except Exception as e:
        logger.error(f"Unexpected error in dashboard for user {uid}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "detail": "An unexpected error occurred while loading dashboard data",
                "error_code": "INTERNAL_ERROR"
            }
        )
