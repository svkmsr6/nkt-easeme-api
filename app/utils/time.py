from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


UTC = timezone.utc


def utcnow() -> datetime:
    """
    Returns timezone-aware current UTC time.
    """
    return datetime.now(UTC)


def ensure_aware(dt: datetime, assume_utc: bool = True) -> datetime:
    """
    Ensure a datetime is timezone-aware. If naive and assume_utc is True,
    interpret as UTC; otherwise raise ValueError.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(UTC)
    if assume_utc:
        return dt.replace(tzinfo=UTC)
    raise ValueError("Naive datetime provided and assume_utc=False")


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
    Add minutes to a (aware or naive) datetime and return UTC-aware datetime.
    """
    base = ensure_aware(dt)
    return base + timedelta(minutes=minutes)


def coerce_interval_minutes(value: int, *, min_minutes: int = 15, max_minutes: int = 120) -> int:
    """
    Clamp a minutes value to allowed bounds.
    """
    if value < min_minutes:
        return min_minutes
    if value > max_minutes:
        return max_minutes
    return value


def is_past(when: Optional[datetime], *, now: Optional[datetime] = None, grace_seconds: int = 0) -> bool:
    """
    True if `when` has passed (optionally with a grace window).
    """
    if when is None:
        return False
    now_ = ensure_aware(now or utcnow())
    target = ensure_aware(when)
    return now_ >= (target + timedelta(seconds=grace_seconds))


def humanize_delta(seconds: int) -> str:
    """
    Simple humanization for durations like '1h 25m' or '17m'.
    """
    if seconds < 0:
        seconds = 0
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)
