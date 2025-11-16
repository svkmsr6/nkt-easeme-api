"""
Unit tests for app.repositories.checkin_repo module.
"""
import pytest
from datetime import datetime, timezone
from app.repositories.checkin_repo import create_checkin, SUGGESTIONS
from app.repositories.task_repo import create_task
from app.repositories.intervention_repo import create_session
from app.db.models import CheckIn


class TestCreateCheckin:
    """Test create_checkin function."""
    
    @pytest.mark.asyncio
    async def test_create_checkin_started_kept_going(self, db_session, test_user_id):
        """Test creating checkin with started_kept_going outcome."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "anxiety_dread",
            "technique_id": "one_minute_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        checkin, suggestion = await create_checkin(
            db_session, test_user_id, session, 
            "started_kept_going", "Going well", "Focused"
        )
        
        assert checkin.id is not None
        assert checkin.user_id == test_user_id
        assert checkin.session_id == session.id
        assert checkin.outcome == "started_kept_going"
        assert checkin.optional_notes == "Going well"
        assert checkin.emotion_after == "Focused"
        assert suggestion == SUGGESTIONS["started_kept_going"]
        assert checkin.created_at is not None
    
    @pytest.mark.asyncio
    async def test_create_checkin_updates_task_last_worked_on(self, db_session, test_user_id):
        """Test that checkin updates task's last_worked_on."""
        task = await create_task(db_session, test_user_id, "Test task")
        original_last_worked = task.last_worked_on
        
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "anxiety_dread",
            "technique_id": "one_minute_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        await create_checkin(
            db_session, test_user_id, session,
            "started_kept_going", None, None
        )
        
        # Refresh task
        await db_session.refresh(task)
        
        # last_worked_on should be updated
        assert task.last_worked_on is not None
        assert task.last_worked_on != original_last_worked
    
    @pytest.mark.asyncio
    async def test_create_checkin_started_stopped(self, db_session, test_user_id):
        """Test checkin with started_stopped outcome."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "anxiety_dread",
            "technique_id": "one_minute_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        checkin, suggestion = await create_checkin(
            db_session, test_user_id, session,
            "started_stopped", "Got distracted", None
        )
        
        assert checkin.outcome == "started_stopped"
        assert suggestion == SUGGESTIONS["started_stopped"]
        
        # Task should still be updated
        await db_session.refresh(task)
        assert task.last_worked_on is not None
    
    @pytest.mark.asyncio
    async def test_create_checkin_did_not_start(self, db_session, test_user_id):
        """Test checkin with did_not_start outcome."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "anxiety_dread",
            "technique_id": "one_minute_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        original_last_worked = task.last_worked_on
        
        checkin, suggestion = await create_checkin(
            db_session, test_user_id, session,
            "did_not_start", "Too tired", "Exhausted"
        )
        
        assert checkin.outcome == "did_not_start"
        assert suggestion == SUGGESTIONS["did_not_start"]
        
        # Task should NOT be updated for did_not_start
        await db_session.refresh(task)
        assert task.last_worked_on == original_last_worked
    
    @pytest.mark.asyncio
    async def test_create_checkin_still_working(self, db_session, test_user_id):
        """Test checkin with still_working outcome."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "anxiety_dread",
            "technique_id": "one_minute_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        checkin, suggestion = await create_checkin(
            db_session, test_user_id, session,
            "still_working", None, None
        )
        
        assert checkin.outcome == "still_working"
        assert suggestion == SUGGESTIONS["still_working"]
        
        # Task should be updated
        await db_session.refresh(task)
        assert task.last_worked_on is not None
    
    @pytest.mark.asyncio
    async def test_create_checkin_without_optional_fields(self, db_session, test_user_id):
        """Test creating checkin without optional notes and emotion."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "anxiety_dread",
            "technique_id": "one_minute_entry",
            "personalized_message": "Just 1 minute",
            "duration_seconds": 60
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        checkin, suggestion = await create_checkin(
            db_session, test_user_id, session,
            "started_kept_going", None, None
        )
        
        assert checkin.optional_notes is None
        assert checkin.emotion_after is None
    
    @pytest.mark.asyncio
    async def test_suggestions_exist_for_all_outcomes(self):
        """Test that suggestions are defined for all valid outcomes."""
        expected_outcomes = {
            "started_kept_going",
            "started_stopped",
            "did_not_start",
            "still_working"
        }
        
        assert set(SUGGESTIONS.keys()) == expected_outcomes
        assert all(isinstance(v, str) for v in SUGGESTIONS.values())
