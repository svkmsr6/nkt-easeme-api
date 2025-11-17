from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InterventionSession
from app.repositories.checkin_repo import create_checkin as repo_create_checkin, SUGGESTIONS
from app.services.clock import clamp_checkin_minutes, default_checkin_minutes, schedule_checkin


VALID_OUTCOMES = {"started_kept_going", "started_stopped", "did_not_start", "still_working"}


@dataclass(slots=True)
class CheckinResult:
    checkin_id: UUID
    suggestion: str
    recommended_next_minutes: int
    scheduled_next_checkin_at: Optional[str]  # ISO string or None


def _recommend_minutes(outcome: str) -> int:
    """
    Policy: suggest an appropriate next window, always within bounds [15, 120].
    - did_not_start       -> 15
    - started_stopped     -> 20
    - started_kept_going  -> 25 (pomodoro-ish)
    - still_working       -> 30
    """
    mapping = {
        "did_not_start": 15,
        "started_stopped": 20,
        "started_kept_going": 25,
        "still_working": 30,
    }
    return clamp_checkin_minutes(mapping.get(outcome, default_checkin_minutes()))


async def create_checkin(
    db: AsyncSession,
    *,
    user_id: UUID,
    session: InterventionSession,
    outcome: str,
    optional_notes: Optional[str] = None,
    emotion_after: Optional[str] = None,
    auto_schedule_next: bool = True,
) -> CheckinResult:
    """
    Orchestrates a check-in creation and computes the next recommendation.
    - Persists the check-in (and updates task.last_worked_on for 'started_*' / 'still_working').
    - Returns a user-facing suggestion and an optional next scheduled check-in timestamp.
    """
    if outcome not in VALID_OUTCOMES:
        raise ValueError("Invalid outcome")

    # Store checkin and get baseline micro-suggestion from repository policy
    ci, base_suggestion = await repo_create_checkin(
        db, user_id, session, outcome, optional_notes, emotion_after
    )

    # Enrich suggestion with a concise next step aligned to the intervention technique used
    technique_hint = _technique_hint(session.technique_id)
    suggestion = f"{base_suggestion} {technique_hint}".strip()

    # Compute a recommended next window and (optionally) schedule on the session
    rec_minutes = _recommend_minutes(outcome)
    scheduled_iso: Optional[str] = None

    if auto_schedule_next:
        next_at = schedule_checkin(session.intervention_started_at or session.created_at, rec_minutes)
        # Persist the scheduled_next time onto the session for the product to surface later
        session.scheduled_checkin_at = next_at
        await db.commit()
        await db.refresh(session)
        scheduled_iso = session.scheduled_checkin_at.isoformat()

    return CheckinResult(
        checkin_id=ci.id,
        suggestion=suggestion,
        recommended_next_minutes=rec_minutes,
        scheduled_next_checkin_at=scheduled_iso,
    )


def _technique_hint(technique_id: Optional[str]) -> str:
    """
    Gentle, technique-specific nudge appended to the base suggestion.
    """
    if not technique_id:
        return ""

    hints = {
        "permission_protocol": "→ Keep permission wide open: it's okay to do this imperfectly.",
        "single_next_action": "→ Identify the smallest next physical action and do only that.",
        "choice_elimination": "→ Skip choosing: follow the single next step you defined.",
        "one_minute_entry": "→ Commit to one minute; you can stop after that if you want.",
    }
    return hints.get(technique_id, "")
