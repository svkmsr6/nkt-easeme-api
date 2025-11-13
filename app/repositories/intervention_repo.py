from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import InterventionSession, Task
from uuid import UUID
from datetime import datetime, timedelta

async def create_session(db: AsyncSession, user_id: UUID, task: Task, payload: dict) -> InterventionSession:
    s = InterventionSession(
        user_id=user_id,
        task_id=task.id,
        physical_sensation=payload["physical_sensation"],
        internal_narrative=payload["internal_narrative"],
        emotion_label=payload["emotion_label"],
        ai_identified_pattern=payload["ai_identified_pattern"],
        technique_id=payload["technique_id"],
        personalized_message=payload["personalized_message"],
        intervention_duration_seconds=payload["duration_seconds"],
    )
    db.add(s); await db.commit(); await db.refresh(s)
    return s

async def get_session_owned(db: AsyncSession, user_id: UUID, session_id: UUID) -> InterventionSession | None:
    res = await db.execute(select(InterventionSession).where(InterventionSession.id==session_id, InterventionSession.user_id==user_id))
    return res.scalar_one_or_none()

async def mark_started_and_schedule(db: AsyncSession, session: InterventionSession, started_at: datetime, minutes: int = 15):
    session.intervention_started_at = started_at
    session.scheduled_checkin_at = started_at + timedelta(minutes=minutes)
    await db.commit(); await db.refresh(session)
    return session.scheduled_checkin_at

async def set_checkin_minutes(db: AsyncSession, session: InterventionSession, minutes: int):
    base = session.intervention_started_at or session.created_at
    session.scheduled_checkin_at = base + timedelta(minutes=minutes)
    await db.commit(); await db.refresh(session)
    return session.scheduled_checkin_at

async def get_recent_sessions(db: AsyncSession, user_id: UUID, limit: int = 5):
    from sqlalchemy.orm import joinedload
    
    q = (
        select(InterventionSession)
        .options(joinedload(InterventionSession.task))
        .where(InterventionSession.user_id==user_id)
        .order_by(InterventionSession.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(q)
    return list(res.scalars())

async def get_pending_checkin(db: AsyncSession, user_id: UUID):
    q = (
        select(InterventionSession)
        .where(
            InterventionSession.user_id==user_id, 
            InterventionSession.scheduled_checkin_at.is_not(None),
            InterventionSession.scheduled_checkin_at <= datetime.utcnow()
        )
        .order_by(InterventionSession.scheduled_checkin_at.asc())
    )
    res = await db.execute(q)
    sessions = list(res.scalars())
    
    # Check if any session has no checkins
    for s in sessions:
        if not s.checkins:  # No checkins yet
            return s
    return None

async def session_detail(s: InterventionSession):
    chk = None
    if s.checkins:
        ci = s.checkins[-1]
        chk = {"outcome": ci.outcome, "created_at": ci.created_at}
    return {
        "session_id": s.id,
        "task": {"task_id": s.task.id, "task_description": s.task.task_description},
        "physical_sensation": s.physical_sensation,
        "internal_narrative": s.internal_narrative,
        "emotion_label": s.emotion_label,
        "technique_id": s.technique_id,
        "personalized_message": s.personalized_message,
        "created_at": s.created_at,
        "scheduled_checkin_at": s.scheduled_checkin_at,
        "checkin": chk,
    }
