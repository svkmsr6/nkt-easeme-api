"""
Unit tests for app.utils.time module.
"""
import pytest
from datetime import datetime, timedelta, timezone
from app.utils.time import (
    utcnow, ensure_aware, add_minutes, coerce_interval_minutes,
    is_past, humanize_delta, UTC
)


class TestUtcNow:
    """Test utcnow function."""
    
    def test_returns_aware_datetime(self):
        """Test that utcnow returns timezone-aware datetime."""
        result = utcnow()
        
        assert result.tzinfo is not None
        assert result.tzinfo == UTC
    
    def test_returns_current_time(self):
        """Test that returned time is approximately now."""
        before = datetime.now(UTC)
        result = utcnow()
        after = datetime.now(UTC)
        
        assert before <= result <= after


class TestEnsureAware:
    """Test ensure_aware function."""
    
    def test_aware_datetime_unchanged(self):
        """Test that aware datetime is converted to UTC."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        result = ensure_aware(dt)
        
        assert result.tzinfo == UTC
        assert result.replace(tzinfo=None) == dt.replace(tzinfo=None)
    
    def test_naive_datetime_assumes_utc(self):
        """Test that naive datetime is assumed to be UTC."""
        dt = datetime(2024, 1, 15, 10, 30)
        result = ensure_aware(dt, assume_utc=True)
        
        assert result.tzinfo == UTC
        assert result.replace(tzinfo=None) == dt
    
    def test_naive_datetime_no_assume_raises(self):
        """Test that naive datetime without assume_utc raises error."""
        dt = datetime(2024, 1, 15, 10, 30)
        
        with pytest.raises(ValueError, match="Naive datetime"):
            ensure_aware(dt, assume_utc=False)
    
    def test_different_timezone_converted(self):
        """Test that different timezone is converted to UTC."""
        # Create datetime in different timezone
        eastern = timezone(timedelta(hours=-5))
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=eastern)
        result = ensure_aware(dt)
        
        assert result.tzinfo == UTC
        # Time should be adjusted by 5 hours
        assert result.hour == 15


class TestAddMinutes:
    """Test add_minutes function."""
    
    def test_add_positive_minutes(self):
        """Test adding positive minutes."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        result = add_minutes(dt, 45)
        
        assert result == datetime(2024, 1, 15, 11, 15, tzinfo=UTC)
    
    def test_add_zero_minutes(self):
        """Test adding zero minutes."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        result = add_minutes(dt, 0)
        
        assert result == dt
    
    def test_add_negative_minutes(self):
        """Test adding negative minutes (subtraction)."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        result = add_minutes(dt, -15)
        
        assert result == datetime(2024, 1, 15, 10, 15, tzinfo=UTC)
    
    def test_add_to_naive_datetime(self):
        """Test adding minutes to naive datetime."""
        dt = datetime(2024, 1, 15, 10, 30)
        result = add_minutes(dt, 30)
        
        assert result.tzinfo == UTC
        assert result.replace(tzinfo=None) == datetime(2024, 1, 15, 11, 0)


class TestCoerceIntervalMinutes:
    """Test coerce_interval_minutes function."""
    
    def test_within_bounds_unchanged(self):
        """Test that values within bounds are unchanged."""
        assert coerce_interval_minutes(30) == 30
        assert coerce_interval_minutes(60) == 60
    
    def test_below_minimum_clamped(self):
        """Test that values below minimum are clamped."""
        assert coerce_interval_minutes(5, min_minutes=15) == 15
        assert coerce_interval_minutes(-10, min_minutes=15) == 15
    
    def test_above_maximum_clamped(self):
        """Test that values above maximum are clamped."""
        assert coerce_interval_minutes(150, max_minutes=120) == 120
        assert coerce_interval_minutes(200, max_minutes=120) == 120
    
    def test_edge_cases(self):
        """Test edge cases at boundaries."""
        assert coerce_interval_minutes(15, min_minutes=15, max_minutes=120) == 15
        assert coerce_interval_minutes(120, min_minutes=15, max_minutes=120) == 120
    
    def test_custom_bounds(self):
        """Test with custom min/max bounds."""
        assert coerce_interval_minutes(5, min_minutes=10, max_minutes=60) == 10
        assert coerce_interval_minutes(30, min_minutes=10, max_minutes=60) == 30
        assert coerce_interval_minutes(100, min_minutes=10, max_minutes=60) == 60


class TestIsPast:
    """Test is_past function."""
    
    def test_past_datetime_returns_true(self):
        """Test that past datetime returns True."""
        past = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        
        assert is_past(past, now=now) is True
    
    def test_future_datetime_returns_false(self):
        """Test that future datetime returns False."""
        future = datetime(2024, 12, 31, 10, 0, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        
        assert is_past(future, now=now) is False
    
    def test_none_returns_false(self):
        """Test that None returns False."""
        assert is_past(None) is False
    
    def test_grace_period(self):
        """Test grace period functionality."""
        target = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 0, 5, tzinfo=UTC)  # 5 seconds later
        
        # Without grace period, should be past
        assert is_past(target, now=now, grace_seconds=0) is True
        
        # With 10 second grace period, should not be past yet
        assert is_past(target, now=now, grace_seconds=10) is False
    
    def test_exact_time_is_past(self):
        """Test that exact same time is considered past."""
        dt = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        
        assert is_past(dt, now=dt) is True


class TestHumanizeDelta:
    """Test humanize_delta function."""
    
    def test_only_minutes(self):
        """Test formatting with only minutes."""
        assert humanize_delta(300) == "5m"  # 5 minutes
        assert humanize_delta(60) == "1m"   # 1 minute
        assert humanize_delta(0) == "0m"    # 0 minutes
    
    def test_hours_and_minutes(self):
        """Test formatting with hours and minutes."""
        assert humanize_delta(3661) == "1h 1m"   # 1 hour, 1 minute
        assert humanize_delta(7200) == "2h 0m"   # 2 hours, 0 minutes
        assert humanize_delta(5400) == "1h 30m"  # 1 hour, 30 minutes
    
    def test_negative_treated_as_zero(self):
        """Test that negative values are treated as zero."""
        assert humanize_delta(-100) == "0m"
    
    def test_seconds_ignored(self):
        """Test that seconds are ignored in output."""
        assert humanize_delta(125) == "2m"  # 2 minutes, 5 seconds -> "2m"
        assert humanize_delta(59) == "0m"   # 59 seconds -> "0m"
