from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import CheckIn, Task, InterventionSession
from uuid import UUID

SUGGESTIONS = {
  "started_kept_going": "Great work getting started.",
  "started_stopped": "Nice start. Small steps count.",
  "did_not_start": "That's okay. Want to try again?",
  "still_working": "Keep going—no pressure. You’ve got this.",
}

async def create_checkin(db: AsyncSession, user_id: UUID, session: InterventionSession, outcome: str, notes: str|None, emotion_after: str|None):
    ci = CheckIn(user_id=user_id, session_id=session.id, outcome=outcome, optional_notes=notes, emotion_after=emotion_after)
    db.add(ci)
    # update last_worked_on if started
    if outcome in ("started_kept_going","started_stopped","still_working"):
        res = await db.execute(select(Task).where(Task.id==session.task_id))
        task = res.scalar_one()
        task.last_worked_on = ci.created_at
    await db.commit(); await db.refresh(ci)
    return ci, SUGGESTIONS[outcome]
