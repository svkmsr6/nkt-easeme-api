from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.utils.time import (
    UTC,
    add_minutes,
    coerce_interval_minutes,
    ensure_aware,
    humanize_delta,
    is_past,
    utcnow,
)

# Business defaults for check-in timing
DEFAULT_CHECKIN_MINUTES = 15
MIN_CHECKIN_MINUTES = 15
MAX_CHECKIN_MINUTES = 120


def default_checkin_minutes() -> int:
    """
    Default check-in window in minutes.
    """
    return DEFAULT_CHECKIN_MINUTES


def clamp_checkin_minutes(value: int) -> int:
    """
    Enforce min/max policy for check-in windows.
    """
    return coerce_interval_minutes(value, min_minutes=MIN_CHECKIN_MINUTES, max_minutes=MAX_CHECKIN_MINUTES)


def schedule_checkin(started_at: Optional[datetime], minutes: int) -> datetime:
    """
    Compute the next check-in timestamp in UTC.
    - If `started_at` is None, we base it on 'now'.
    - `minutes` is clamped to policy bounds.
    """
    mins = clamp_checkin_minutes(minutes)
    base = ensure_aware(started_at or utcnow())
    return add_minutes(base, mins)


def is_checkin_due(scheduled_at: Optional[datetime], *, grace_seconds: int = 0, now: Optional[datetime] = None) -> bool:
    """
    Whether a scheduled check-in is due now.
    """
    return is_past(scheduled_at, now=now, grace_seconds=grace_seconds)


def eta_text(scheduled_at: Optional[datetime], *, now: Optional[datetime] = None) -> str:
    """
    Human-readable time-to-checkin string like 'in 15m' or 'due'.
    """
    if scheduled_at is None:
        return "unscheduled"
    n = ensure_aware(now or utcnow())
    s = ensure_aware(scheduled_at)
    seconds = int((s - n).total_seconds())
    if seconds <= 0:
        return "due"
    return f"in {humanize_delta(seconds)}"
