from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.api.deps import Authed
from app.schemas.checkin import CheckinCreate, CheckinOut
from app.repositories.intervention_repo import get_session_owned
from app.repositories.checkin_repo import create_checkin

router = APIRouter(prefix="/api/checkins", tags=["checkins"])

VALID = {"started_kept_going","started_stopped","did_not_start","still_working"}

@router.post("", response_model=CheckinOut, status_code=201)
async def create(payload: CheckinCreate, ctx=Depends(Authed)):
    if payload.outcome not in VALID:
        raise HTTPException(status_code=400, detail="Invalid outcome value")
    s = await get_session_owned(ctx["db"], ctx["user_id"], payload.session_id)
    if not s: raise HTTPException(status_code=404, detail="Session not found or doesn't belong to user")
    ci, suggestion = await create_checkin(ctx["db"], ctx["user_id"], s, payload.outcome, payload.optional_notes, payload.emotion_after)
    return {"checkin_id": ci.id, "created_at": ci.created_at, "suggestion": suggestion}
