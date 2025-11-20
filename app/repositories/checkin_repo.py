from sqlalchemy.orm import Session
from sqlalchemy import select, text
from app.db.models import CheckIn, Task, InterventionSession
from uuid import UUID

SUGGESTIONS = {
  "started_kept_going": "Great work getting started.",
  "started_stopped": "Nice start. Small steps count.",
  "did_not_start": "That's okay. Want to try again?",
  "still_working": "Keep going—no pressure. You’ve got this.",
}

def create_checkin(db: Session, user_id: UUID, session: InterventionSession, outcome: str, notes: str|None, emotion_after: str|None):
    ci = CheckIn(user_id=user_id, session_id=session.id, outcome=outcome, optional_notes=notes, emotion_after=emotion_after)
    db.add(ci)
    # update last_worked_on if started
    if outcome in ("started_kept_going","started_stopped","still_working"):
        # Use direct SQL update to avoid potential type casting issues
        db.execute(
            text("UPDATE app.tasks SET last_worked_on = NOW() WHERE id = :task_id"),
            {"task_id": session.task_id}
        )
    db.commit(); db.refresh(ci)
    return ci, SUGGESTIONS[outcome]
