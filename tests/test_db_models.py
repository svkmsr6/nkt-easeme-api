"""
Unit tests for app.db.models module.
"""
import pytest
import uuid
from datetime import datetime
from app.db.models import Task, InterventionSession, CheckIn


class TestTaskModel:
    """Test Task model."""
    
    async def test_task_creation(self, db_session, test_user_id):
        """Test creating a Task instance."""
        task = Task(
            user_id=test_user_id,
            task_description="Test task"
        )
        db_session.add(task)
        await db_session.flush()  # Flush to generate ID
        
        assert task.user_id == test_user_id
        assert task.task_description == "Test task"
        assert task.id is not None  # UUID should be generated
        assert isinstance(task.id, uuid.UUID)
    
    async def test_task_defaults(self, db_session, test_user_id):
        """Test Task default values."""
        task = Task(
            user_id=test_user_id,
            task_description="Test"
        )
        db_session.add(task)
        await db_session.flush()  # Flush to apply defaults
        
        assert task.status == "active"  # Default status
        assert task.last_worked_on is None
    
    def test_task_relationships(self):
        """Test Task relationship setup."""
        task = Task(user_id=uuid.uuid4(), task_description="Test")
        
        # Should have sessions relationship
        assert hasattr(task, 'sessions')
        assert isinstance(task.sessions, list)


class TestInterventionSessionModel:
    """Test InterventionSession model."""
    
    def test_session_creation(self):
        """Test creating an InterventionSession instance."""
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        
        session = InterventionSession(
            user_id=user_id,
            task_id=task_id,
            physical_sensation="Tense shoulders",
            internal_narrative="I can't do this",
            emotion_label="Anxiety"
        )
        
        assert session.user_id == user_id
        assert session.task_id == task_id
        assert session.physical_sensation == "Tense shoulders"
        assert session.internal_narrative == "I can't do this"
        assert session.emotion_label == "Anxiety"
    
    def test_session_optional_fields(self):
        """Test InterventionSession optional fields."""
        session = InterventionSession(
            user_id=uuid.uuid4(),
            task_id=uuid.uuid4()
        )
        
        assert session.physical_sensation is None
        assert session.internal_narrative is None
        assert session.emotion_label is None
        assert session.ai_identified_pattern is None
        assert session.technique_id is None
        assert session.personalized_message is None
        assert session.intervention_duration_seconds is None
        assert session.intervention_started_at is None
        assert session.scheduled_checkin_at is None
    
    def test_session_relationships(self):
        """Test InterventionSession relationships."""
        session = InterventionSession(
            user_id=uuid.uuid4(),
            task_id=uuid.uuid4()
        )
        
        # Should have task and checkins relationships
        assert hasattr(session, 'task')
        assert hasattr(session, 'checkins')
        assert isinstance(session.checkins, list)


class TestCheckInModel:
    """Test CheckIn model."""
    
    def test_checkin_creation(self):
        """Test creating a CheckIn instance."""
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        checkin = CheckIn(
            user_id=user_id,
            session_id=session_id,
            outcome="started_kept_going"
        )
        
        assert checkin.user_id == user_id
        assert checkin.session_id == session_id
        assert checkin.outcome == "started_kept_going"
    
    def test_checkin_optional_fields(self):
        """Test CheckIn optional fields."""
        checkin = CheckIn(
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            outcome="did_not_start"
        )
        
        assert checkin.optional_notes is None
        assert checkin.emotion_after is None
    
    def test_checkin_with_notes(self):
        """Test CheckIn with optional notes."""
        checkin = CheckIn(
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            outcome="started_stopped",
            optional_notes="Got interrupted",
            emotion_after="Frustrated"
        )
        
        assert checkin.optional_notes == "Got interrupted"
        assert checkin.emotion_after == "Frustrated"
    
    def test_checkin_relationships(self):
        """Test CheckIn relationships."""
        checkin = CheckIn(
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            outcome="still_working"
        )
        
        # Should have session relationship
        assert hasattr(checkin, 'session')


class TestModelSchemas:
    """Test model schema configuration."""
    
    def test_models_use_app_schema(self):
        """Test that all models use 'app' schema."""
        assert Task.__table_args__.get('schema') == 'app'
        assert InterventionSession.__table_args__.get('schema') == 'app'
        assert CheckIn.__table_args__.get('schema') == 'app'
    
    def test_table_names(self):
        """Test table names are correct."""
        assert Task.__tablename__ == 'tasks'
        assert InterventionSession.__tablename__ == 'intervention_sessions'
        assert CheckIn.__tablename__ == 'checkins'
