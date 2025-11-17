"""
Unit tests for app.services.clock module.
"""
import pytest
from datetime import datetime, timedelta, timezone
from app.services.clock import (
    default_checkin_minutes, clamp_checkin_minutes, schedule_checkin,
    is_checkin_due, eta_text, DEFAULT_CHECKIN_MINUTES,
    MIN_CHECKIN_MINUTES, MAX_CHECKIN_MINUTES
)
from app.utils.time import UTC


class TestDefaultCheckinMinutes:
    """Test default_checkin_minutes function."""
    
    def test_returns_default_value(self):
        """Test that it returns the expected default."""
        assert default_checkin_minutes() == DEFAULT_CHECKIN_MINUTES
        assert default_checkin_minutes() == 15


class TestClampCheckinMinutes:
    """Test clamp_checkin_minutes function."""
    
    def test_within_bounds_unchanged(self):
        """Test values within bounds are unchanged."""
        assert clamp_checkin_minutes(20) == 20
        assert clamp_checkin_minutes(60) == 60
        assert clamp_checkin_minutes(100) == 100
    
    def test_below_minimum_clamped(self):
        """Test values below minimum are clamped."""
        assert clamp_checkin_minutes(5) == MIN_CHECKIN_MINUTES
        assert clamp_checkin_minutes(0) == MIN_CHECKIN_MINUTES
        assert clamp_checkin_minutes(-10) == MIN_CHECKIN_MINUTES
    
    def test_above_maximum_clamped(self):
        """Test values above maximum are clamped."""
        assert clamp_checkin_minutes(150) == MAX_CHECKIN_MINUTES
        assert clamp_checkin_minutes(200) == MAX_CHECKIN_MINUTES
    
    def test_boundary_values(self):
        """Test boundary values."""
        assert clamp_checkin_minutes(MIN_CHECKIN_MINUTES) == MIN_CHECKIN_MINUTES
        assert clamp_checkin_minutes(MAX_CHECKIN_MINUTES) == MAX_CHECKIN_MINUTES


class TestScheduleCheckin:
    """Test schedule_checkin function."""
    
    def test_schedule_from_datetime(self):
        """Test scheduling from a specific datetime."""
        started = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        result = schedule_checkin(started, 30)
        
        expected = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        assert result == expected
    
    def test_schedule_from_none_uses_now(self):
        """Test that None uses current time."""
        before = datetime.now(UTC)
        result = schedule_checkin(None, 15)
        after = datetime.now(UTC) + timedelta(minutes=15)
        
        # Result should be approximately 15 minutes from now
        assert before + timedelta(minutes=14) <= result <= after
    
    def test_clamps_minutes(self):
        """Test that minutes are clamped to policy bounds."""
        started = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        
        # Below minimum
        result = schedule_checkin(started, 5)
        expected = datetime(2024, 1, 15, 10, 15, tzinfo=UTC)  # Clamped to 15
        assert result == expected
        
        # Above maximum
        result = schedule_checkin(started, 200)
        expected = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)  # Clamped to 120
        assert result == expected
    
    def test_handles_naive_datetime(self):
        """Test handling of naive datetime."""
        started = datetime(2024, 1, 15, 10, 0)  # Naive
        result = schedule_checkin(started, 30)
        
        assert result.tzinfo == UTC
        assert result.hour == 10
        assert result.minute == 30


class TestIsCheckinDue:
    """Test is_checkin_due function."""
    
    def test_past_time_is_due(self):
        """Test that past time is due."""
        scheduled = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        
        assert is_checkin_due(scheduled, now=now) is True
    
    def test_future_time_not_due(self):
        """Test that future time is not due."""
        scheduled = datetime(2024, 1, 15, 11, 0, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        
        assert is_checkin_due(scheduled, now=now) is False
    
    def test_none_not_due(self):
        """Test that None is not due."""
        assert is_checkin_due(None) is False
    
    def test_grace_period(self):
        """Test grace period functionality."""
        scheduled = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 0, 5, tzinfo=UTC)  # 5 seconds after
        
        # Without grace, is due
        assert is_checkin_due(scheduled, grace_seconds=0, now=now) is True
        
        # With 10 second grace (future), not yet due (needs to be 10s past scheduled)
        now_before_grace = datetime(2024, 1, 15, 10, 0, 5, tzinfo=UTC)  # Only 5s past
        assert is_checkin_due(scheduled, grace_seconds=10, now=now_before_grace) is False
        
        # With 10 second grace and 10s past, now due
        now_after_grace = datetime(2024, 1, 15, 10, 0, 10, tzinfo=UTC)
        assert is_checkin_due(scheduled, grace_seconds=10, now=now_after_grace) is True
    
    def test_exact_time_is_due(self):
        """Test that exact scheduled time is due."""
        dt = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        
        assert is_checkin_due(dt, now=dt) is True


class TestEtaText:
    """Test eta_text function."""
    
    def test_none_returns_unscheduled(self):
        """Test None returns 'unscheduled'."""
        assert eta_text(None) == "unscheduled"
    
    def test_past_time_returns_due(self):
        """Test past time returns 'due'."""
        scheduled = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        
        assert eta_text(scheduled, now=now) == "due"
    
    def test_future_time_returns_formatted(self):
        """Test future time returns formatted string."""
        scheduled = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        
        result = eta_text(scheduled, now=now)
        assert result.startswith("in ")
        assert "30m" in result
    
    def test_hours_and_minutes_format(self):
        """Test formatting with hours and minutes."""
        scheduled = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
        now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        
        result = eta_text(scheduled, now=now)
        assert result.startswith("in ")
        assert "1h" in result
        assert "30m" in result
    
    def test_exact_time_returns_due(self):
        """Test exact scheduled time returns 'due'."""
        dt = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        
        assert eta_text(dt, now=dt) == "due"
