"""
Unit tests for app.repositories.intervention_repo module.
"""
import pytest
import uuid
from datetime import datetime, timezone
from app.repositories.intervention_repo import (
    create_session, get_session_owned, mark_started_and_schedule,
    set_checkin_minutes, get_recent_sessions, get_pending_checkin,
    session_detail
)
from app.repositories.task_repo import create_task
from app.db.models import InterventionSession


class TestCreateSession:
    """Test create_session function."""
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, db_session, test_user_id):
        """Test creating an intervention session."""
        # Create a task first
        task = await create_task(db_session, test_user_id, "Test task")
        
        payload = {
            "physical_sensation": "Tight chest",
            "internal_narrative": "I'll never finish",
            "emotion_label": "Overwhelmed",
            "ai_identified_pattern": "overwhelm",
            "technique_id": "single_next_action",
            "personalized_message": "Focus on one small step",
            "duration_seconds": 60
        }
        
        session = await create_session(db_session, test_user_id, task, payload)
        
        assert session.id is not None
        assert session.user_id == test_user_id
        assert session.task_id == task.id
        assert session.physical_sensation == "Tight chest"
        assert session.internal_narrative == "I'll never finish"
        assert session.emotion_label == "Overwhelmed"
        assert session.ai_identified_pattern == "overwhelm"
        assert session.technique_id == "single_next_action"
        assert session.personalized_message == "Focus on one small step"
        assert session.intervention_duration_seconds == 60


class TestGetSessionOwned:
    """Test get_session_owned function."""
    
    @pytest.mark.asyncio
    async def test_get_existing_session(self, db_session, test_user_id):
        """Test getting an existing session with relationships loaded."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "fear",
            "technique_id": "1min_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        result = await get_session_owned(db_session, test_user_id, session.id)
        
        assert result is not None
        assert result.id == session.id
        assert result.task is not None
        assert result.task.id == task.id
        assert isinstance(result.checkins, list)
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, db_session, test_user_id):
        """Test getting nonexistent session returns None."""
        fake_id = uuid.uuid4()
        
        result = await get_session_owned(db_session, test_user_id, fake_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_session_wrong_user(self, db_session, test_user_id, another_user_id):
        """Test getting session owned by another user returns None."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "fear",
            "technique_id": "1min_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        result = await get_session_owned(db_session, another_user_id, session.id)
        
        assert result is None


class TestMarkStartedAndSchedule:
    """Test mark_started_and_schedule function."""
    
    @pytest.mark.asyncio
    async def test_mark_started_and_schedule(self, db_session, test_user_id):
        """Test marking session as started and scheduling checkin."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "fear",
            "technique_id": "1min_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        started_at = datetime.now(timezone.utc)
        scheduled = await mark_started_and_schedule(db_session, session, started_at, minutes=15)
        
        assert session.intervention_started_at is not None
        assert session.scheduled_checkin_at is not None
        assert scheduled == session.scheduled_checkin_at
        assert scheduled is not None
        
        # Check that scheduled time is approximately 15 minutes after started
        delta = (scheduled.replace(tzinfo=timezone.utc) - 
                started_at.replace(tzinfo=None)).total_seconds()
        assert 14 * 60 <= delta <= 16 * 60  # Within 1 minute tolerance


class TestSetCheckinMinutes:
    """Test set_checkin_minutes function."""
    
    @pytest.mark.asyncio
    async def test_set_checkin_minutes(self, db_session, test_user_id):
        """Test updating scheduled checkin time."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "fear",
            "technique_id": "1min_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        # Mark as started
        started_at = datetime.now(timezone.utc)
        await mark_started_and_schedule(db_session, session, started_at, minutes=15)
        
        # Change to 30 minutes
        new_scheduled = await set_checkin_minutes(db_session, session, 30)
        
        assert session.scheduled_checkin_at == new_scheduled
        assert new_scheduled is not None
        
        # Check that new scheduled time is approximately 30 minutes after started
        delta = (new_scheduled.replace(tzinfo=timezone.utc) - 
                started_at.replace(tzinfo=None)).total_seconds()
        assert 29 * 60 <= delta <= 31 * 60


class TestGetRecentSessions:
    """Test get_recent_sessions function."""
    
    @pytest.mark.asyncio
    async def test_get_recent_sessions(self, db_session, test_user_id):
        """Test getting recent sessions for a user."""
        task = await create_task(db_session, test_user_id, "Test task")
        
        # Create multiple sessions
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "fear",
            "technique_id": "1min_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        
        session1 = await create_session(db_session, test_user_id, task, payload)
        session2 = await create_session(db_session, test_user_id, task, payload)
        session3 = await create_session(db_session, test_user_id, task, payload)
        
        sessions = await get_recent_sessions(db_session, test_user_id, limit=5)
        
        assert len(sessions) == 3
        # Should be ordered by created_at desc (newest first)
        assert sessions[0].id == session3.id
        assert sessions[1].id == session2.id
        assert sessions[2].id == session1.id
    
    @pytest.mark.asyncio
    async def test_get_recent_sessions_with_limit(self, db_session, test_user_id):
        """Test getting recent sessions respects limit."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "fear",
            "technique_id": "1min_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        
        # Create 10 sessions
        for _ in range(10):
            await create_session(db_session, test_user_id, task, payload)
        
        sessions = await get_recent_sessions(db_session, test_user_id, limit=3)
        
        assert len(sessions) == 3


class TestSessionDetail:
    """Test session_detail function."""
    
    @pytest.mark.asyncio
    async def test_session_detail_format(self, db_session, test_user_id):
        """Test session detail returns properly formatted data."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tight chest",
            "internal_narrative": "Can't finish",
            "emotion_label": "Overwhelmed",
            "ai_identified_pattern": "overwhelm",
            "technique_id": "single_next_action",
            "personalized_message": "One step at a time",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        detail = await session_detail(session)
        
        assert detail["session_id"] == session.id
        assert detail["task"]["task_id"] == task.id
        assert detail["task"]["task_description"] == "Test task"
        assert detail["physical_sensation"] == "Tight chest"
        assert detail["internal_narrative"] == "Can't finish"
        assert detail["emotion_label"] == "Overwhelmed"
        assert detail["technique_id"] == "single_next_action"
        assert detail["personalized_message"] == "One step at a time"
        assert detail["checkin"] is None  # No checkin yet
