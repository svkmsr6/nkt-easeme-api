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
        intervention_type="timer",
        intervention_duration_seconds=payload["duration_seconds"],
    )
    db.add(s); await db.commit(); await db.refresh(s)
    return s

async def get_session_owned(db: AsyncSession, user_id: UUID, session_id: UUID) -> InterventionSession | None:
    res = await db.execute(select(InterventionSession).where(InterventionSession.id==session_id, InterventionSession.user_id==user_id))
    return res.scalar_one_or_none()

async def mark_started_and_schedule(db: AsyncSession, session: InterventionSession, started_at: datetime, minutes: int = 15):
    session.started_at = started_at
    session.scheduled_checkin_at = started_at + timedelta(minutes=minutes)
    await db.commit(); await db.refresh(session)
    return session.scheduled_checkin_at

async def set_checkin_minutes(db: AsyncSession, session: InterventionSession, minutes: int):
    base = session.started_at or session.created_at
    session.scheduled_checkin_at = base + timedelta(minutes=minutes)
    await db.commit(); await db.refresh(session)
    return session.scheduled_checkin_at

async def get_recent_sessions(db: AsyncSession, user_id: UUID, limit: int = 5):
    from sqlalchemy.orm import joinedload
    from sqlalchemy.exc import ProgrammingError
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        q = (
            select(InterventionSession)
            .options(joinedload(InterventionSession.task))
            .where(InterventionSession.user_id==user_id)
            .order_by(InterventionSession.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(q)
        return list(res.scalars())
    except ProgrammingError as e:
        # Check if this is a column not found error
        if "intervention_type" in str(e) and "does not exist" in str(e):
            logger.warning(f"Column 'intervention_type' not found in database, falling back to basic query")
            # Try a more basic query without the problematic column
            try:
                # Select only the columns we know exist
                basic_q = (
                    select(InterventionSession.id, 
                           InterventionSession.user_id,
                           InterventionSession.task_id,
                           InterventionSession.created_at,
                           InterventionSession.technique_id)
                    .where(InterventionSession.user_id==user_id)
                    .order_by(InterventionSession.created_at.desc())
                    .limit(limit)
                )
                basic_res = await db.execute(basic_q)
                
                # Manually construct InterventionSession-like objects
                sessions = []
                for row in basic_res:
                    # Get the task separately
                    task_q = select(Task).where(Task.id == row.task_id)
                    task_res = await db.execute(task_q)
                    task = task_res.scalar_one_or_none()
                    
                    # Create a minimal session object
                    session = type('Session', (), {
                        'id': row.id,
                        'user_id': row.user_id,
                        'task_id': row.task_id,
                        'created_at': row.created_at,
                        'technique_id': row.technique_id,
                        'task': task
                    })()
                    sessions.append(session)
                
                return sessions
            except Exception as fallback_e:
                logger.error(f"Fallback query also failed: {fallback_e}")
                return []
        else:
            # Re-raise other ProgrammingErrors
            raise

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
