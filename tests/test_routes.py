"""
Integration tests for API routes.
"""
import pytest
from unittest.mock import patch, Mock
from httpx import Response


class TestHealthRoute:
    """Test /health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health endpoint returns OK."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestTasksRoutes:
    """Test /api/tasks endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_tasks_invalid_status_fails(self, client):
        """Test that invalid status parameter fails validation."""
        response = await client.get("/api/tasks?status=invalid")
        
        assert response.status_code == 422  # Validation error


class TestAIRoutes:
    """Test /api/ai endpoints."""
    
    @pytest.mark.asyncio
    async def test_emotion_labels(self, client, mock_emotion_labels_response):
        """Test emotion labels generation."""
        payload = {
            "task_description": "Present to board",
            "physical_sensation": "Sweaty palms",
            "internal_narrative": "They'll think I'm incompetent"
        }
        
        with patch("app.services.ai.httpx.AsyncClient") as mock_client:
            mock_post = Mock()
            mock_resp = Mock()
            mock_resp.json = Mock(return_value=mock_emotion_labels_response)
            mock_resp.raise_for_status = Mock()
            mock_post.return_value = mock_resp
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            response = await client.post("/api/ai/emotion-labels", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "emotion_options" in data
        assert isinstance(data["emotion_options"], list)
        assert len(data["emotion_options"]) <= 3


class TestDashboardRoute:
    """Test /api/user/dashboard endpoint."""
    
    @pytest.mark.asyncio
    async def test_dashboard(self, client):
        """Test dashboard endpoint."""
        response = await client.get("/api/user/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_tasks" in data
        assert "recent_sessions" in data
        assert "pending_checkin" in data
        assert isinstance(data["active_tasks"], list)
        assert isinstance(data["recent_sessions"], list)
