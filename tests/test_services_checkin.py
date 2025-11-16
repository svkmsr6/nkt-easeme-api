"""
Unit tests for app.services.checkin module.
"""
import pytest
from datetime import datetime, timezone
from app.services.checkin import (
    create_checkin, _recommend_minutes, _technique_hint,
    VALID_OUTCOMES
)
from app.repositories.task_repo import create_task
from app.repositories.intervention_repo import create_session


class TestRecommendMinutes:
    """Test _recommend_minutes function."""
    
    def test_did_not_start_recommends_15(self):
        """Test did_not_start recommends 15 minutes."""
        assert _recommend_minutes("did_not_start") == 15
    
    def test_started_stopped_recommends_20(self):
        """Test started_stopped recommends 20 minutes."""
        assert _recommend_minutes("started_stopped") == 20
    
    def test_started_kept_going_recommends_25(self):
        """Test started_kept_going recommends 25 minutes."""
        assert _recommend_minutes("started_kept_going") == 25
    
    def test_still_working_recommends_30(self):
        """Test still_working recommends 30 minutes."""
        assert _recommend_minutes("still_working") == 30
    
    def test_unknown_outcome_uses_default(self):
        """Test unknown outcome uses default."""
        result = _recommend_minutes("unknown_outcome")
        # Should use default and clamp to valid range
        assert 15 <= result <= 120


class TestTechniqueHint:
    """Test _technique_hint function."""
    
    def test_permission_protocol_hint(self):
        """Test hint for permission_protocol."""
        hint = _technique_hint("permission_protocol")
        
        assert "permission" in hint.lower()
        assert "imperfect" in hint.lower()
    
    def test_single_next_action_hint(self):
        """Test hint for single_next_action."""
        hint = _technique_hint("single_next_action")
        
        assert "smallest" in hint.lower() or "next" in hint.lower()
    
    def test_choice_elimination_hint(self):
        """Test hint for choice_elimination."""
        hint = _technique_hint("choice_elimination")
        
        assert "skip" in hint.lower() or "choosing" in hint.lower()
    
    def test_one_minute_entry_hint(self):
        """Test hint for one_minute_entry."""
        hint = _technique_hint("one_minute_entry")
        
        assert "minute" in hint.lower()
    
    def test_unknown_technique_returns_empty(self):
        """Test unknown technique returns empty string."""
        hint = _technique_hint("unknown_technique")
        
        assert hint == ""
    
    def test_none_technique_returns_empty(self):
        """Test None technique returns empty string."""
        hint = _technique_hint(None)
        
        assert hint == ""


class TestCreateCheckin:
    """Test create_checkin service function."""
    
    @pytest.mark.asyncio
    async def test_create_checkin_with_auto_schedule(self, db_session, test_user_id):
        """Test creating checkin with auto scheduling."""
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
        
        # Mark as started
        from app.repositories.intervention_repo import mark_started_and_schedule
        await mark_started_and_schedule(db_session, session, datetime.now(timezone.utc), 15)
        
        result = await create_checkin(
            db_session,
            user_id=test_user_id,
            session=session,
            outcome="started_kept_going",
            optional_notes="Making progress",
            emotion_after="Focused",
            auto_schedule_next=True
        )
        
        assert result.checkin_id is not None
        assert result.suggestion is not None
        assert isinstance(result.recommended_next_minutes, int)
        assert result.recommended_next_minutes == 25  # For started_kept_going
        assert result.scheduled_next_checkin_at is not None
    
    @pytest.mark.asyncio
    async def test_create_checkin_without_auto_schedule(self, db_session, test_user_id):
        """Test creating checkin without auto scheduling."""
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
        
        result = await create_checkin(
            db_session,
            user_id=test_user_id,
            session=session,
            outcome="did_not_start",
            auto_schedule_next=False
        )
        
        assert result.checkin_id is not None
        assert result.scheduled_next_checkin_at is None
    
    @pytest.mark.asyncio
    async def test_create_checkin_invalid_outcome_raises_error(self, db_session, test_user_id):
        """Test that invalid outcome raises ValueError."""
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
        
        with pytest.raises(ValueError, match="Invalid outcome"):
            await create_checkin(
                db_session,
                user_id=test_user_id,
                session=session,
                outcome="invalid_outcome"
            )
    
    @pytest.mark.asyncio
    async def test_create_checkin_suggestion_includes_technique_hint(self, db_session, test_user_id):
        """Test that suggestion includes technique-specific hint."""
        task = await create_task(db_session, test_user_id, "Test task")
        payload = {
            "physical_sensation": "Tense",
            "internal_narrative": "Worried",
            "emotion_label": "Anxiety",
            "ai_identified_pattern": "perfectionism",
            "technique_id": "permission_protocol",
            "personalized_message": "Allow imperfection",
            "duration_seconds": 300
        }
        session = await create_session(db_session, test_user_id, task, payload)
        
        result = await create_checkin(
            db_session,
            user_id=test_user_id,
            session=session,
            outcome="started_kept_going",
            auto_schedule_next=False
        )
        
        # Should include technique hint
        assert "permission" in result.suggestion.lower() or "imperfect" in result.suggestion.lower()
    
    @pytest.mark.asyncio
    async def test_valid_outcomes_constant(self):
        """Test VALID_OUTCOMES contains expected values."""
        expected_outcomes = {
            "started_kept_going",
            "started_stopped",
            "did_not_start",
            "still_working"
        }
        
        assert VALID_OUTCOMES == expected_outcomes
