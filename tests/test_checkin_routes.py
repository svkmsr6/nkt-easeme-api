"""
Comprehensive tests for checkin routes.
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime, timezone

class TestCheckinRoutes:
    """Test checkin endpoints."""
    
    def test_create_checkin_success_started_kept_going(self, sync_client):
        """Test successful checkin creation with started_kept_going outcome."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "started_kept_going",
            "optional_notes": "Went well",
            "emotion_after": "calm"
        }
        
        # Mock the dependencies
        mock_session = Mock()
        mock_session.id = session_id
        
        mock_checkin = Mock()
        mock_checkin.id = str(uuid4())
        mock_checkin.created_at = datetime.now(timezone.utc)
        
        with patch('app.api.routes.checkins.get_session_owned') as mock_get_session:
            with patch('app.api.routes.checkins.create_checkin') as mock_create:
                mock_get_session.return_value = mock_session
                mock_create.return_value = (mock_checkin, "Great work!")
                
                response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["checkin_id"] == mock_checkin.id
        assert "created_at" in data
        assert data["suggestion"] == "Great work!"
    
    def test_create_checkin_success_started_stopped(self, sync_client):
        """Test successful checkin creation with started_stopped outcome."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "started_stopped",
            "optional_notes": "Had to stop early",
            "emotion_after": "frustrated"
        }
        
        mock_session = Mock()
        mock_session.id = session_id
        
        mock_checkin = Mock()
        mock_checkin.id = str(uuid4())
        mock_checkin.created_at = datetime.now(timezone.utc)
        
        with patch('app.api.routes.checkins.get_session_owned') as mock_get_session:
            with patch('app.api.routes.checkins.create_checkin') as mock_create:
                mock_get_session.return_value = mock_session
                mock_create.return_value = (mock_checkin, "It's okay to stop when needed")
                
                response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["checkin_id"] == mock_checkin.id
        assert data["suggestion"] == "It's okay to stop when needed"
    
    def test_create_checkin_success_did_not_start(self, sync_client):
        """Test successful checkin creation with did_not_start outcome."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "did_not_start",
            "optional_notes": "Too tired today",
            "emotion_after": "disappointed"
        }
        
        mock_session = Mock()
        mock_checkin = Mock()
        mock_checkin.id = str(uuid4())
        mock_checkin.created_at = datetime.now(timezone.utc)
        
        with patch('app.api.routes.checkins.get_session_owned') as mock_get_session:
            with patch('app.api.routes.checkins.create_checkin') as mock_create:
                mock_get_session.return_value = mock_session
                mock_create.return_value = (mock_checkin, "Tomorrow is a new day")
                
                response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 201
    
    def test_create_checkin_success_still_working(self, sync_client):
        """Test successful checkin creation with still_working outcome."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "still_working",
            "optional_notes": "Making progress",
            "emotion_after": "focused"
        }
        
        mock_session = Mock()
        mock_checkin = Mock()
        mock_checkin.id = str(uuid4())
        mock_checkin.created_at = datetime.now(timezone.utc)
        
        with patch('app.api.routes.checkins.get_session_owned') as mock_get_session:
            with patch('app.api.routes.checkins.create_checkin') as mock_create:
                mock_get_session.return_value = mock_session
                mock_create.return_value = (mock_checkin, "Keep going!")
                
                response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 201
    
    def test_create_checkin_invalid_outcome(self, sync_client):
        """Test checkin creation with invalid outcome value."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "invalid_outcome",
            "optional_notes": "Some notes",
            "emotion_after": "neutral"
        }
        
        response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid outcome value" in data["detail"]
    
    def test_create_checkin_session_not_found(self, sync_client):
        """Test checkin creation when session is not found."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "started_kept_going",
            "optional_notes": "Some notes",
            "emotion_after": "happy"
        }
        
        with patch('app.api.routes.checkins.get_session_owned') as mock_get_session:
            mock_get_session.return_value = None  # Session not found
            
            response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 404
        data = response.json()
        assert "Session not found or doesn't belong to user" in data["detail"]
    
    def test_create_checkin_session_not_owned_by_user(self, sync_client):
        """Test checkin creation when session doesn't belong to user."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "started_kept_going",
            "optional_notes": "Some notes",
            "emotion_after": "happy"
        }
        
        with patch('app.api.routes.checkins.get_session_owned') as mock_get_session:
            mock_get_session.return_value = None  # User doesn't own session
            
            response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 404
        data = response.json()
        assert "Session not found or doesn't belong to user" in data["detail"]
    
    def test_create_checkin_minimal_data(self, sync_client):
        """Test checkin creation with minimal required data."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "started_kept_going"
            # No optional_notes or emotion_after
        }
        
        mock_session = Mock()
        mock_checkin = Mock()
        mock_checkin.id = str(uuid4())
        mock_checkin.created_at = datetime.now(timezone.utc)
        
        with patch('app.api.routes.checkins.get_session_owned') as mock_get_session:
            with patch('app.api.routes.checkins.create_checkin') as mock_create:
                mock_get_session.return_value = mock_session
                mock_create.return_value = (mock_checkin, "Good job!")
                
                response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert "checkin_id" in data
        assert "created_at" in data
        assert "suggestion" in data
    
    def test_valid_outcomes_constant(self):
        """Test that VALID outcomes constant contains expected values."""
        from app.api.routes.checkins import VALID
        
        expected_outcomes = {
            "started_kept_going",
            "started_stopped", 
            "did_not_start",
            "still_working"
        }
        
        assert VALID == expected_outcomes
        assert len(VALID) == 4
        
    def test_create_checkin_with_empty_notes(self, sync_client):
        """Test checkin creation with empty optional notes."""
        session_id = str(uuid4())
        payload = {
            "session_id": session_id,
            "outcome": "started_kept_going",
            "optional_notes": "",
            "emotion_after": "content"
        }
        
        mock_session = Mock()
        mock_checkin = Mock()
        mock_checkin.id = str(uuid4())
        mock_checkin.created_at = datetime.now(timezone.utc)
        
        with patch('app.api.routes.checkins.get_session_owned') as mock_get_session:
            with patch('app.api.routes.checkins.create_checkin') as mock_create:
                mock_get_session.return_value = mock_session
                mock_create.return_value = (mock_checkin, "Well done!")
                
                response = sync_client.post("/api/checkins", json=payload)
        
        assert response.status_code == 201
        # Verify the create_checkin was called with empty string for notes
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        assert args[4] == ""  # optional_notes parameter (5th argument)