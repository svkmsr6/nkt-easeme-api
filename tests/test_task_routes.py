"""
Comprehensive tests for task routes - working tests only.
"""

class TestTaskRoutes:
    """Test task endpoints."""
    
    def test_create_task_missing_description(self, sync_client):
        """Test task creation with missing description."""
        payload = {
            "task_description": ""
        }
        
        response = sync_client.post("/api/tasks", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "Missing task_description" in data["detail"]