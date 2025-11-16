"""
Unit tests for app.services.ai module.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch
from httpx import Response, RequestError, HTTPStatusError
from app.services.ai import choose_intervention, emotion_labels, FALLBACKS


class TestChooseIntervention:
    """Test choose_intervention function."""
    
    @pytest.mark.asyncio
    async def test_choose_intervention_success(self, mock_openai_response):
        """Test successful intervention selection."""
        payload = {
            "task_description": "Write report",
            "physical_sensation": "Tight shoulders",
            "internal_narrative": "It has to be perfect",
            "emotion_label": "Anxious"
        }
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            # Create a proper mock response
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json = AsyncMock(return_value=mock_openai_response)
            mock_resp.raise_for_status = AsyncMock()
            mock_post.return_value = mock_resp
            
            result = await choose_intervention(payload)
            
            assert "pattern" in result
            assert "technique_id" in result
            assert "message" in result
            assert "duration_seconds" in result
            assert result["pattern"] == "perfectionism"
            assert result["technique_id"] == "permission_protocol"
    
    @pytest.mark.asyncio
    async def test_choose_intervention_network_error_uses_fallback(self):
        """Test that network errors use fallback."""
        payload = {
            "task_description": "Write report",
            "physical_sensation": "Tight shoulders",
            "internal_narrative": "It has to be perfect",
            "emotion_label": "Anxious"
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = RequestError("Connection failed")
            
            result = await choose_intervention(payload)
            
            # Should return a fallback
            assert result["pattern"] == "anxiety_dread"
            assert result["technique_id"] == FALLBACKS["anxiety_dread"]["technique_id"]
    
    @pytest.mark.asyncio
    async def test_choose_intervention_http_error_uses_fallback(self):
        """Test that HTTP errors use fallback."""
        payload = {
            "task_description": "Write report",
            "physical_sensation": "Tight shoulders",
            "internal_narrative": "It has to be perfect",
            "emotion_label": "Anxious"
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            error_response = Response(status_code=500, json={"error": "Server error"})
            mock_post.return_value = error_response
            error_response.request = AsyncMock()
            
            # Simulate raise_for_status behavior
            def raise_for_status():
                raise HTTPStatusError("Server error", request=error_response.request, response=error_response)
            error_response.raise_for_status = raise_for_status
            
            result = await choose_intervention(payload)
            
            # Should return fallback
            assert "pattern" in result
            assert result["pattern"] == "anxiety_dread"
    
    @pytest.mark.asyncio
    async def test_choose_intervention_invalid_json_uses_fallback(self):
        """Test that invalid JSON response uses fallback."""
        payload = {
            "task_description": "Write report",
            "physical_sensation": "Tight shoulders",
            "internal_narrative": "It has to be perfect",
            "emotion_label": "Anxious"
        }
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            # Return coroutine that resolves to dict with invalid JSON content
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "not valid json"}}]
            })
            mock_response.raise_for_status = AsyncMock()
            mock_post.return_value = mock_response
            
            result = await choose_intervention(payload)
            
            # Should return fallback due to JSON decode error
            assert result["pattern"] == "anxiety_dread"
    
    @pytest.mark.asyncio
    async def test_fallbacks_defined_for_all_patterns(self):
        """Test that fallbacks exist for all expected patterns."""
        expected_patterns = {
            "perfectionism",
            "overwhelm",
            "decision_fatigue",
            "anxiety_dread"
        }
        
        assert set(FALLBACKS.keys()) == expected_patterns
        
        for pattern, fallback in FALLBACKS.items():
            assert "technique_id" in fallback
            assert "message" in fallback
            assert "duration_seconds" in fallback
            assert isinstance(fallback["duration_seconds"], int)


class TestEmotionLabels:
    """Test emotion_labels function."""
    
    @pytest.mark.asyncio
    async def test_emotion_labels_success(self, mock_emotion_labels_response):
        """Test successful emotion label generation."""
        payload = {
            "task_description": "Presentation",
            "physical_sensation": "Racing heart",
            "internal_narrative": "Everyone will judge me"
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_emotion_labels_response,
                request=None
            )
            
            result = await emotion_labels(payload)
            
            assert isinstance(result, list)
            assert len(result) <= 3
            assert "Fear of judgment" in result
    
    @pytest.mark.asyncio
    async def test_emotion_labels_timeout_uses_default(self):
        """Test that timeout returns default labels."""
        payload = {
            "task_description": "Presentation",
            "physical_sensation": "Racing heart",
            "internal_narrative": "Everyone will judge me"
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            from httpx import TimeoutException
            mock_post.side_effect = TimeoutException("Request timeout")
            
            result = await emotion_labels(payload)
            
            # Should return default labels
            assert isinstance(result, list)
            assert len(result) == 3
            assert "Fear of judgment" in result
            assert "Perfectionism anxiety" in result
            assert "Performance pressure" in result
    
    @pytest.mark.asyncio
    async def test_emotion_labels_connection_error_uses_default(self):
        """Test that connection errors return default labels."""
        payload = {
            "task_description": "Presentation",
            "physical_sensation": "Racing heart",
            "internal_narrative": "Everyone will judge me"
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            from httpx import ConnectError
            mock_post.side_effect = ConnectError("Cannot connect")
            
            result = await emotion_labels(payload)
            
            # Should return default labels
            assert isinstance(result, list)
            assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_emotion_labels_limits_to_three(self):
        """Test that emotion labels are limited to 3."""
        payload = {
            "task_description": "Presentation",
            "physical_sensation": "Racing heart",
            "internal_narrative": "Everyone will judge me"
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            # Return more than 3 labels
            mock_response = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "labels": ["Label1", "Label2", "Label3", "Label4", "Label5"]
                        })
                    }
                }]
            }
            mock_post.return_value = Response(
                status_code=200,
                json=mock_response,
                request=None
            )
            
            result = await emotion_labels(payload)
            
            # Should only return first 3
            assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_emotion_labels_handles_emotion_options_key(self):
        """Test that function handles both 'labels' and 'emotion_options' keys."""
        payload = {
            "task_description": "Presentation",
            "physical_sensation": "Racing heart",
            "internal_narrative": "Everyone will judge me"
        }
        
        with patch("app.services.ai.httpx.AsyncClient.post") as mock_post:
            mock_response = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "emotion_options": ["Nervous", "Worried", "Stressed"]
                        })
                    }
                }]
            }
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_resp.raise_for_status = AsyncMock()
            mock_post.return_value = mock_resp
            
            result = await emotion_labels(payload)
            
            assert result == ["Nervous", "Worried", "Stressed"]
