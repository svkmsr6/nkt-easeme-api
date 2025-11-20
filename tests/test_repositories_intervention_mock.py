"""
Unit tests for app.repositories.intervention_repo module using mocks.
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, MagicMock
from app.repositories.intervention_repo import (
    create_session, get_session_owned, mark_started_and_schedule,
    set_checkin_minutes, get_recent_sessions, get_pending_checkin,
    session_detail
)
from app.db.models import InterventionSession, Task, CheckIn


class TestCreateSession:
    """Test create_session function with mocked database."""
    
    def test_create_session_success(self):
        """Test creating an intervention session with mocked DB."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        task = Mock(spec=Task)
        task.id = uuid.uuid4()
        
        payload = {
            "physical_sensation": "Tight chest",
            "internal_narrative": "I'll never finish",
            "emotion_label": "Overwhelmed",
            "ai_identified_pattern": "overwhelm",
            "technique_id": "single_next_action",
            "personalized_message": "Focus on one small step",
            "duration_seconds": 60
        }
        
        # Execute
        session = create_session(db_mock, user_id, task, payload)
        
        # Verify
        assert session.user_id == user_id
        assert session.task_id == task.id
        assert session.physical_sensation == "Tight chest"
        assert session.internal_narrative == "I'll never finish"
        assert session.emotion_label == "Overwhelmed"
        assert session.ai_identified_pattern == "overwhelm"
        assert session.technique_id == "single_next_action"
        assert session.personalized_message == "Focus on one small step"
        assert session.intervention_duration_seconds == 60
        
        # Verify DB operations
        db_mock.add.assert_called_once()
        db_mock.commit.assert_called_once()
        db_mock.refresh.assert_called_once()


class TestGetSessionOwned:
    """Test get_session_owned function with mocked database."""
    
    def test_get_existing_session(self):
        """Test getting an existing session."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.id = session_id
        mock_session.user_id = user_id
        
        result_mock = Mock()
        result_mock.unique = Mock(return_value=result_mock)
        result_mock.scalar_one_or_none = Mock(return_value=mock_session)
        db_mock.execute = Mock(return_value=result_mock)
        
        # Execute
        result = get_session_owned(db_mock, user_id, session_id)
        
        # Verify
        assert result == mock_session
        db_mock.execute.assert_called_once()
    
    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        result_mock = Mock()
        result_mock.unique = Mock(return_value=result_mock)
        result_mock.scalar_one_or_none = Mock(return_value=None)
        db_mock.execute = Mock(return_value=result_mock)
        
        # Execute
        result = get_session_owned(db_mock, user_id, session_id)
        
        # Verify
        assert result is None


class TestMarkStartedAndSchedule:
    """Test mark_started_and_schedule function."""
    
    def test_mark_started_with_timezone_aware_datetime(self):
        """Test marking session as started with timezone-aware datetime."""
        # Setup
        db_mock = Mock()
        session = Mock(spec=InterventionSession)
        started_at = datetime.now(timezone.utc)
        minutes = 20
        
        # Execute
        result = mark_started_and_schedule(db_mock, session, started_at, minutes)
        
        # Verify
        assert session.intervention_started_at is not None
        assert session.intervention_started_at.tzinfo is None  # Should strip timezone
        assert session.scheduled_checkin_at is not None
        db_mock.commit.assert_called_once()
        db_mock.refresh.assert_called_once()
    
    def test_mark_started_with_naive_datetime(self):
        """Test marking session as started with naive datetime."""
        # Setup
        db_mock = Mock()
        session = Mock(spec=InterventionSession)
        started_at = datetime.now()  # Naive datetime
        minutes = 15
        
        # Execute
        result = mark_started_and_schedule(db_mock, session, started_at, minutes)
        
        # Verify
        assert session.intervention_started_at == started_at
        assert session.scheduled_checkin_at == started_at + timedelta(minutes=15)


class TestSetCheckinMinutes:
    """Test set_checkin_minutes function."""
    
    def test_set_checkin_minutes_with_started_at(self):
        """Test setting checkin minutes when intervention_started_at is set."""
        # Setup
        db_mock = Mock()
        session = Mock(spec=InterventionSession)
        started_at = datetime.now()
        session.intervention_started_at = started_at
        session.created_at = datetime.now() - timedelta(hours=1)
        minutes = 30
        
        # Execute
        result = set_checkin_minutes(db_mock, session, minutes)
        
        # Verify
        assert session.scheduled_checkin_at == started_at + timedelta(minutes=30)
        db_mock.commit.assert_called_once()
        db_mock.refresh.assert_called_once()
    
    def test_set_checkin_minutes_without_started_at(self):
        """Test setting checkin minutes when intervention_started_at is None."""
        # Setup
        db_mock = Mock()
        session = Mock(spec=InterventionSession)
        session.intervention_started_at = None
        created_at = datetime.now()
        session.created_at = created_at
        minutes = 25
        
        # Execute
        result = set_checkin_minutes(db_mock, session, minutes)
        
        # Verify
        assert session.scheduled_checkin_at == created_at + timedelta(minutes=25)


class TestGetRecentSessions:
    """Test get_recent_sessions function."""
    
    def test_get_recent_sessions_default_limit(self):
        """Test getting recent sessions with default limit."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        
        mock_sessions = [Mock(spec=InterventionSession) for _ in range(3)]
        
        result_mock = Mock()
        result_mock.scalars = Mock(return_value=mock_sessions)
        db_mock.execute = Mock(return_value=result_mock)
        
        # Execute
        result = get_recent_sessions(db_mock, user_id)
        
        # Verify
        assert len(result) == 3
        db_mock.execute.assert_called_once()
    
    def test_get_recent_sessions_custom_limit(self):
        """Test getting recent sessions with custom limit."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        
        mock_sessions = [Mock(spec=InterventionSession) for _ in range(10)]
        
        result_mock = Mock()
        result_mock.scalars = Mock(return_value=mock_sessions)
        db_mock.execute = Mock(return_value=result_mock)
        
        # Execute
        result = get_recent_sessions(db_mock, user_id, limit=10)
        
        # Verify
        assert len(result) == 10


class TestGetPendingCheckin:
    """Test get_pending_checkin function."""
    
    def test_get_pending_checkin_with_no_checkins(self):
        """Test getting pending checkin when session has no checkins."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.checkins = []
        mock_session.scheduled_checkin_at = datetime.now() - timedelta(minutes=5)
        
        result_mock = Mock()
        result_mock.scalars = Mock(return_value=[mock_session])
        db_mock.execute = Mock(return_value=result_mock)
        
        # Execute
        result = get_pending_checkin(db_mock, user_id)
        
        # Verify
        assert result == mock_session
    
    def test_get_pending_checkin_all_have_checkins(self):
        """Test getting pending checkin when all sessions have checkins."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        
        mock_session = Mock(spec=InterventionSession)
        mock_checkin = Mock(spec=CheckIn)
        mock_session.checkins = [mock_checkin]
        
        result_mock = Mock()
        result_mock.scalars = Mock(return_value=[mock_session])
        db_mock.execute = Mock(return_value=result_mock)
        
        # Execute
        result = get_pending_checkin(db_mock, user_id)
        
        # Verify
        assert result is None
    
    def test_get_pending_checkin_no_sessions(self):
        """Test getting pending checkin when no sessions exist."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        
        result_mock = Mock()
        result_mock.scalars = Mock(return_value=[])
        db_mock.execute = Mock(return_value=result_mock)
        
        # Execute
        result = get_pending_checkin(db_mock, user_id)
        
        # Verify
        assert result is None


class TestSessionDetail:
    """Test session_detail function."""
    
    def test_session_detail_with_checkin(self):
        """Test session detail when checkin exists."""
        # Setup
        mock_task = Mock(spec=Task)
        mock_task.id = uuid.uuid4()
        mock_task.task_description = "Test task"
        
        mock_checkin = Mock(spec=CheckIn)
        mock_checkin.outcome = "started_kept_going"
        mock_checkin.created_at = datetime.now()
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.id = uuid.uuid4()
        mock_session.task = mock_task
        mock_session.physical_sensation = "Tense"
        mock_session.internal_narrative = "Worried"
        mock_session.emotion_label = "Anxious"
        mock_session.technique_id = "permission_protocol"
        mock_session.personalized_message = "You have permission"
        mock_session.created_at = datetime.now()
        mock_session.scheduled_checkin_at = datetime.now() + timedelta(minutes=15)
        mock_session.checkins = [mock_checkin]
        
        # Execute
        result = session_detail(mock_session)
        
        # Verify
        assert result["session_id"] == mock_session.id
        assert result["task"]["task_id"] == mock_task.id
        assert result["task"]["task_description"] == "Test task"
        assert result["physical_sensation"] == "Tense"
        assert result["internal_narrative"] == "Worried"
        assert result["emotion_label"] == "Anxious"
        assert result["technique_id"] == "permission_protocol"
        assert result["personalized_message"] == "You have permission"
        assert result["checkin"] is not None
        assert result["checkin"]["outcome"] == "started_kept_going"
    
    def test_session_detail_without_checkin(self):
        """Test session detail when no checkin exists."""
        # Setup
        mock_task = Mock(spec=Task)
        mock_task.id = uuid.uuid4()
        mock_task.task_description = "Another task"
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.id = uuid.uuid4()
        mock_session.task = mock_task
        mock_session.physical_sensation = "Calm"
        mock_session.internal_narrative = "I can do this"
        mock_session.emotion_label = "Confident"
        mock_session.technique_id = "single_next_action"
        mock_session.personalized_message = "Just one step"
        mock_session.created_at = datetime.now()
        mock_session.scheduled_checkin_at = None
        mock_session.checkins = []
        
        # Execute
        result = session_detail(mock_session)
        
        # Verify
        assert result["session_id"] == mock_session.id
        assert result["checkin"] is None
