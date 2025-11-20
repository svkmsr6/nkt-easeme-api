from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import InterventionSession, Task
from uuid import UUID
from datetime import datetime, timedelta

def create_session(db: Session, user_id: UUID, task: Task, payload: dict) -> InterventionSession:
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
    db.add(s); db.commit(); db.refresh(s)
    return s

def get_session_owned(db: Session, user_id: UUID, session_id: UUID) -> InterventionSession | None:
    from sqlalchemy.orm import joinedload, selectinload
    
    q = (
        select(InterventionSession)
        .options(joinedload(InterventionSession.task), selectinload(InterventionSession.checkins))
        .where(InterventionSession.id==session_id, InterventionSession.user_id==user_id)
    )
    res = db.execute(q)
    return res.unique().scalar_one_or_none()

def mark_started_and_schedule(db: Session, session: InterventionSession, started_at: datetime, minutes: int = 15):
    # Strip timezone info since DB columns are TIMESTAMP WITHOUT TIME ZONE
    started_naive = started_at.replace(tzinfo=None) if started_at.tzinfo else started_at
    session.intervention_started_at = started_naive
    session.scheduled_checkin_at = started_naive + timedelta(minutes=minutes)
    db.commit(); db.refresh(session)
    return session.scheduled_checkin_at

def set_checkin_minutes(db: Session, session: InterventionSession, minutes: int):
    base = session.intervention_started_at or session.created_at
    session.scheduled_checkin_at = base + timedelta(minutes=minutes)
    db.commit(); db.refresh(session)
    return session.scheduled_checkin_at

def get_recent_sessions(db: Session, user_id: UUID, limit: int = 5):
    from sqlalchemy.orm import joinedload
    
    q = (
        select(InterventionSession)
        .options(joinedload(InterventionSession.task))
        .where(InterventionSession.user_id==user_id)
        .order_by(InterventionSession.created_at.desc())
        .limit(limit)
    )
    res = db.execute(q)
    return list(res.scalars())

def get_pending_checkin(db: Session, user_id: UUID):
    q = (
        select(InterventionSession)
        .where(
            InterventionSession.user_id==user_id, 
            InterventionSession.scheduled_checkin_at.is_not(None),
            InterventionSession.scheduled_checkin_at <= datetime.utcnow()
        )
        .order_by(InterventionSession.scheduled_checkin_at.asc())
    )
    res = db.execute(q)
    sessions = list(res.scalars())
    
    # Check if any session has no checkins
    for s in sessions:
        if not s.checkins:  # No checkins yet
            return s
    return None

def session_detail(s: InterventionSession):
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
