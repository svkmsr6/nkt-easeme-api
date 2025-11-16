"""
Integration tests for API routes.
"""
import pytest
import uuid
from unittest.mock import patch
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
    async def test_create_task(self, client):
        """Test creating a task."""
        payload = {"task_description": "Write tests"}
        
        response = await client.post("/api/tasks", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["task_description"] == "Write tests"
        assert "id" in data
        assert data["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_create_task_empty_description_fails(self, client):
        """Test creating task with empty description fails."""
        payload = {"task_description": ""}
        
        response = await client.post("/api/tasks", json=payload)
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, client):
        """Test listing tasks."""
        # Create a couple of tasks first
        await client.post("/api/tasks", json={"task_description": "Task 1"})
        await client.post("/api/tasks", json={"task_description": "Task 2"})
        
        response = await client.get("/api/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 2
    
    @pytest.mark.asyncio
    async def test_list_tasks_filter_by_status(self, client):
        """Test filtering tasks by status."""
        response = await client.get("/api/tasks?status=active")
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
    
    @pytest.mark.asyncio
    async def test_list_tasks_invalid_status_fails(self, client):
        """Test that invalid status parameter fails validation."""
        response = await client.get("/api/tasks?status=invalid")
        
        assert response.status_code == 422  # Validation error


class TestInterventionsRoutes:
    """Test /api/interventions endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_intervention(self, client, mock_openai_response):
        """Test creating an intervention session."""
        # Create a task first
        task_response = await client.post("/api/tasks", json={"task_description": "Big project"})
        task_id = task_response.json()["id"]
        
        payload = {
            "task_id": task_id,
            "physical_sensation": "Tight chest",
            "internal_narrative": "Too much to do",
            "emotion_label": "Overwhelmed"
        }
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_openai_response,
                request=None
            )
            
            response = await client.post("/api/interventions", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "technique_id" in data
        assert "personalized_message" in data
        assert "intervention_duration_seconds" in data
    
    @pytest.mark.asyncio
    async def test_create_intervention_invalid_task_fails(self, client, mock_openai_response):
        """Test creating intervention with invalid task fails."""
        payload = {
            "task_id": str(uuid.uuid4()),
            "physical_sensation": "Tense",
            "internal_narrative": "Can't do it",
            "emotion_label": "Anxious"
        }
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_openai_response,
                request=None
            )
            
            response = await client.post("/api/interventions", json=payload)
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_start_session(self, client, mock_openai_response):
        """Test starting an intervention session."""
        # Create task and intervention
        task_response = await client.post("/api/tasks", json={"task_description": "Test"})
        task_id = task_response.json()["id"]
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_openai_response,
                request=None
            )
            
            intervention_response = await client.post("/api/interventions", json={
                "task_id": task_id,
                "physical_sensation": "Tense",
                "internal_narrative": "Worried",
                "emotion_label": "Anxious"
            })
        
        session_id = intervention_response.json()["id"]
        
        response = await client.post(f"/api/interventions/{session_id}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "scheduled_checkin_at" in data
    
    @pytest.mark.asyncio
    async def test_patch_checkin_time(self, client, mock_openai_response):
        """Test updating checkin time."""
        # Create task, intervention, and start session
        task_response = await client.post("/api/tasks", json={"task_description": "Test"})
        task_id = task_response.json()["id"]
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_openai_response,
                request=None
            )
            
            intervention_response = await client.post("/api/interventions", json={
                "task_id": task_id,
                "physical_sensation": "Tense",
                "internal_narrative": "Worried",
                "emotion_label": "Anxious"
            })
        
        session_id = intervention_response.json()["id"]
        await client.post(f"/api/interventions/{session_id}/start")
        
        # Update checkin time
        response = await client.patch(
            f"/api/interventions/{session_id}/checkin-time",
            json={"checkin_minutes": 30}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "scheduled_checkin_at" in data
    
    @pytest.mark.asyncio
    async def test_get_intervention_detail(self, client, mock_openai_response):
        """Test getting intervention session details."""
        # Create task and intervention
        task_response = await client.post("/api/tasks", json={"task_description": "Test"})
        task_id = task_response.json()["id"]
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_openai_response,
                request=None
            )
            
            intervention_response = await client.post("/api/interventions", json={
                "task_id": task_id,
                "physical_sensation": "Tense",
                "internal_narrative": "Worried",
                "emotion_label": "Anxious"
            })
        
        session_id = intervention_response.json()["id"]
        
        response = await client.get(f"/api/interventions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "task" in data
        assert "technique_id" in data


class TestCheckinsRoutes:
    """Test /api/checkins endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_checkin(self, client, mock_openai_response):
        """Test creating a checkin."""
        # Create task, intervention, and start session
        task_response = await client.post("/api/tasks", json={"task_description": "Test"})
        task_id = task_response.json()["id"]
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_openai_response,
                request=None
            )
            
            intervention_response = await client.post("/api/interventions", json={
                "task_id": task_id,
                "physical_sensation": "Tense",
                "internal_narrative": "Worried",
                "emotion_label": "Anxious"
            })
        
        session_id = intervention_response.json()["id"]
        await client.post(f"/api/interventions/{session_id}/start")
        
        # Create checkin
        payload = {
            "session_id": session_id,
            "outcome": "started_kept_going",
            "optional_notes": "Going well",
            "emotion_after": "Focused"
        }
        
        response = await client.post("/api/checkins", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert "checkin_id" in data
        assert "suggestion" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_checkin_invalid_outcome(self, client, mock_openai_response):
        """Test creating checkin with invalid outcome fails."""
        # Create minimal session
        task_response = await client.post("/api/tasks", json={"task_description": "Test"})
        task_id = task_response.json()["id"]
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_openai_response,
                request=None
            )
            
            intervention_response = await client.post("/api/interventions", json={
                "task_id": task_id,
                "physical_sensation": "Tense",
                "internal_narrative": "Worried",
                "emotion_label": "Anxious"
            })
        
        session_id = intervention_response.json()["id"]
        
        payload = {
            "session_id": session_id,
            "outcome": "invalid_outcome"
        }
        
        response = await client.post("/api/checkins", json=payload)
        
        assert response.status_code == 400


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
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_emotion_labels_response,
                request=None
            )
            
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
    
    @pytest.mark.asyncio
    async def test_dashboard_with_data(self, client, mock_openai_response):
        """Test dashboard with actual data."""
        # Create some tasks
        await client.post("/api/tasks", json={"task_description": "Task 1"})
        await client.post("/api/tasks", json={"task_description": "Task 2"})
        
        response = await client.get("/api/user/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["active_tasks"]) >= 2
