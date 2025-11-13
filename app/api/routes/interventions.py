from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from app.api.deps import Authed
from app.schemas.intervention import InterventionCreate, InterventionOut, StartSessionIn, StartSessionOut, CheckinTimePatchIn, InterventionDetailOut
from app.repositories.task_repo import get_task_owned
from app.repositories.intervention_repo import create_session, get_session_owned, mark_started_and_schedule, set_checkin_minutes, session_detail
from app.services.ai import choose_intervention

router = APIRouter(prefix="/api/interventions", tags=["interventions"])

@router.post("", response_model=InterventionOut, status_code=201)
async def create_intervention(payload: InterventionCreate, ctx=Depends(Authed)):
    db: AsyncSession = ctx["db"]; user_id = ctx["user_id"]
    try:
        task = await get_task_owned(db, user_id, payload.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found or doesn't belong to user")
        # AI
        ai = await choose_intervention({
            "task_description": task.task_description,
            "physical_sensation": payload.physical_sensation,
            "internal_narrative": payload.internal_narrative,
            "emotion_label": payload.emotion_label,
        })
        s = await create_session(db, user_id, task, {
            "physical_sensation": payload.physical_sensation,
            "internal_narrative": payload.internal_narrative,
            "emotion_label": payload.emotion_label,
            "ai_identified_pattern": ai["pattern"],
            "technique_id": ai["technique_id"],
            "personalized_message": ai["message"],
            "duration_seconds": ai["duration_seconds"],
        })
        return {
            "id": s.id,
            "ai_identified_pattern": s.ai_identified_pattern,
            "technique_id": s.technique_id,
            "personalized_message": s.personalized_message,
            "intervention_duration_seconds": s.intervention_duration_seconds or 60
        }
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Error creating intervention: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e

@router.post("/{session_id}/start", response_model=StartSessionOut)
async def start_session(session_id: UUID = Path(...), payload: StartSessionIn | None = None, ctx=Depends(Authed)):
    db: AsyncSession = ctx["db"]; user_id = ctx["user_id"]
    s = await get_session_owned(db, user_id, session_id)
    if not s: raise HTTPException(status_code=404, detail="Session not found or doesn't belong to user")
    started_at = payload.started_at if payload else datetime.utcnow()
    scheduled = await mark_started_and_schedule(db, s, started_at, minutes=15)
    return {"success": True, "scheduled_checkin_at": scheduled}

@router.patch("/{session_id}/checkin-time")
async def patch_checkin_time(session_id: UUID, payload: CheckinTimePatchIn, ctx=Depends(Authed)):
    db: AsyncSession = ctx["db"]; user_id = ctx["user_id"]
    s = await get_session_owned(db, user_id, session_id)
    if not s: raise HTTPException(status_code=404, detail="Session not found or doesn't belong to user")
    scheduled = await set_checkin_minutes(db, s, payload.checkin_minutes)
    return {"scheduled_checkin_at": scheduled}

@router.get("/{session_id}", response_model=InterventionDetailOut)
async def get_detail(session_id: UUID, ctx=Depends(Authed)):
    db: AsyncSession = ctx["db"]; user_id = ctx["user_id"]
    s = await get_session_owned(db, user_id, session_id)
    if not s: raise HTTPException(status_code=404, detail="Session not found or doesn't belong to user")
    return await session_detail(s)
