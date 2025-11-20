"""
Unit tests for checkin repository functions using mocks.
"""
import pytest
import uuid
from unittest.mock import Mock
from datetime import datetime
from app.repositories.checkin_repo import create_checkin, SUGGESTIONS
from app.db.models import CheckIn, InterventionSession


class TestCreateCheckin:
    """Test create_checkin function."""
    
    def test_create_checkin_started_kept_going(self):
        """Test creating checkin with 'started_kept_going' outcome."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.id = session_id
        mock_session.task_id = task_id
        
        outcome = "started_kept_going"
        notes = "Made good progress"
        emotion_after = "Satisfied"
        
        mock_checkin = Mock(spec=CheckIn)
        mock_checkin.id = uuid.uuid4()
        mock_checkin.user_id = user_id
        mock_checkin.session_id = session_id
        mock_checkin.outcome = outcome
        mock_checkin.optional_notes = notes
        mock_checkin.emotion_after = emotion_after
        mock_checkin.created_at = datetime.now()
        
        # Mock database operations
        def mock_add(checkin):
            checkin.id = mock_checkin.id
            checkin.created_at = mock_checkin.created_at
        
        db_mock.add.side_effect = mock_add
        db_mock.execute.return_value = None  # For the SQL update
        db_mock.commit.return_value = None
        db_mock.refresh.return_value = None
        
        # Execute
        result_checkin, suggestion = create_checkin(db_mock, user_id, mock_session, outcome, notes, emotion_after)
        
        # Verify
        assert result_checkin.user_id == user_id
        assert result_checkin.session_id == session_id
        assert result_checkin.outcome == outcome
        assert result_checkin.optional_notes == notes
        assert result_checkin.emotion_after == emotion_after
        assert suggestion == SUGGESTIONS[outcome]
        
        # Verify database operations
        db_mock.add.assert_called_once()
        db_mock.execute.assert_called_once()  # Should update last_worked_on
        db_mock.commit.assert_called_once()
        db_mock.refresh.assert_called_once()
    
    def test_create_checkin_started_stopped(self):
        """Test creating checkin with 'started_stopped' outcome."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.id = session_id
        mock_session.task_id = task_id
        
        outcome = "started_stopped"
        notes = None
        emotion_after = "Tired"
        
        mock_checkin = Mock(spec=CheckIn)
        mock_checkin.id = uuid.uuid4()
        mock_checkin.user_id = user_id
        mock_checkin.session_id = session_id
        mock_checkin.outcome = outcome
        mock_checkin.optional_notes = notes
        mock_checkin.emotion_after = emotion_after
        
        def mock_add(checkin):
            checkin.id = mock_checkin.id
        
        db_mock.add.side_effect = mock_add
        db_mock.execute.return_value = None
        db_mock.commit.return_value = None
        db_mock.refresh.return_value = None
        
        # Execute
        result_checkin, suggestion = create_checkin(db_mock, user_id, mock_session, outcome, notes, emotion_after)
        
        # Verify
        assert result_checkin.outcome == outcome
        assert suggestion == SUGGESTIONS[outcome]
        
        # Should still update last_worked_on for started_stopped
        db_mock.execute.assert_called_once()
    
    def test_create_checkin_still_working(self):
        """Test creating checkin with 'still_working' outcome."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.id = session_id
        mock_session.task_id = task_id
        
        outcome = "still_working"
        notes = "Making steady progress"
        emotion_after = "Focused"
        
        mock_checkin = Mock(spec=CheckIn)
        mock_checkin.outcome = outcome
        
        def mock_add(checkin):
            checkin.id = uuid.uuid4()
        
        db_mock.add.side_effect = mock_add
        db_mock.execute.return_value = None
        db_mock.commit.return_value = None
        db_mock.refresh.return_value = None
        
        # Execute
        result_checkin, suggestion = create_checkin(db_mock, user_id, mock_session, outcome, notes, emotion_after)
        
        # Verify
        assert result_checkin.outcome == outcome
        assert suggestion == SUGGESTIONS[outcome]
        
        # Should update last_worked_on for still_working
        db_mock.execute.assert_called_once()
    
    def test_create_checkin_did_not_start(self):
        """Test creating checkin with 'did_not_start' outcome."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.id = session_id
        mock_session.task_id = task_id
        
        outcome = "did_not_start"
        notes = "Too overwhelmed today"
        emotion_after = "Disappointed"
        
        mock_checkin = Mock(spec=CheckIn)
        mock_checkin.outcome = outcome
        
        def mock_add(checkin):
            checkin.id = uuid.uuid4()
        
        db_mock.add.side_effect = mock_add
        db_mock.commit.return_value = None
        db_mock.refresh.return_value = None
        
        # Execute
        result_checkin, suggestion = create_checkin(db_mock, user_id, mock_session, outcome, notes, emotion_after)
        
        # Verify
        assert result_checkin.outcome == outcome
        assert suggestion == SUGGESTIONS[outcome]
        
        # Should NOT update last_worked_on for did_not_start
        db_mock.execute.assert_not_called()
        db_mock.commit.assert_called_once()
        db_mock.refresh.assert_called_once()
    
    def test_create_checkin_minimal_data(self):
        """Test creating checkin with minimal data (no notes, no emotion)."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        mock_session = Mock(spec=InterventionSession)
        mock_session.id = session_id
        mock_session.task_id = task_id
        
        outcome = "started_kept_going"
        notes = None
        emotion_after = None
        
        mock_checkin = Mock(spec=CheckIn)
        mock_checkin.outcome = outcome
        mock_checkin.optional_notes = None
        mock_checkin.emotion_after = None
        
        def mock_add(checkin):
            checkin.id = uuid.uuid4()
        
        db_mock.add.side_effect = mock_add
        db_mock.execute.return_value = None
        db_mock.commit.return_value = None
        db_mock.refresh.return_value = None
        
        # Execute
        result_checkin, suggestion = create_checkin(db_mock, user_id, mock_session, outcome, notes, emotion_after)
        
        # Verify
        assert result_checkin.outcome == outcome
        assert result_checkin.optional_notes is None
        assert result_checkin.emotion_after is None
        assert suggestion == SUGGESTIONS[outcome]


class TestSuggestions:
    """Test SUGGESTIONS constant."""
    
    def test_all_suggestions_exist(self):
        """Test that all expected suggestion keys exist."""
        expected_outcomes = [
            "started_kept_going",
            "started_stopped", 
            "did_not_start",
            "still_working"
        ]
        
        for outcome in expected_outcomes:
            assert outcome in SUGGESTIONS
            assert isinstance(SUGGESTIONS[outcome], str)
            assert len(SUGGESTIONS[outcome]) > 0
    
    def test_suggestion_content(self):
        """Test specific suggestion content."""
        assert "Great work" in SUGGESTIONS["started_kept_going"]
        assert "Nice start" in SUGGESTIONS["started_stopped"]
        assert "okay" in SUGGESTIONS["did_not_start"]
        assert "Keep going" in SUGGESTIONS["still_working"]