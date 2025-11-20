"""
Unit tests for task repository functions using mocks.
"""
import pytest
import uuid
from unittest.mock import Mock
from datetime import datetime
from app.repositories.task_repo import create_task, get_task_owned, list_tasks
from app.db.models import Task


class TestCreateTask:
    """Test create_task function."""
    
    def test_create_task_success(self):
        """Test successful task creation."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        description = "Test task description"
        
        # Mock task object
        mock_task = Mock(spec=Task)
        mock_task.id = uuid.uuid4()
        mock_task.user_id = user_id
        mock_task.task_description = description
        mock_task.status = "active"
        mock_task.created_at = datetime.now()
        mock_task.last_worked_on = None
        
        # Mock database operations
        def mock_add(task):
            # Simulate setting ID after add
            task.id = mock_task.id
            task.status = "active"
            task.created_at = mock_task.created_at
        
        db_mock.add.side_effect = mock_add
        db_mock.commit.return_value = None
        db_mock.refresh.return_value = None
        
        # Execute
        result = create_task(db_mock, user_id, description)
        
        # Verify
        assert result.user_id == user_id
        assert result.task_description == description
        db_mock.add.assert_called_once()
        db_mock.commit.assert_called_once()
        db_mock.refresh.assert_called_once()


class TestGetTaskOwned:
    """Test get_task_owned function."""
    
    def test_get_existing_task(self):
        """Test getting an existing task owned by user."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.user_id = user_id
        mock_task.task_description = "Test task"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_task
        db_mock.execute.return_value = mock_result
        
        # Execute
        result = get_task_owned(db_mock, user_id, task_id)
        
        # Verify
        assert result == mock_task
        db_mock.execute.assert_called_once()
        mock_result.scalar_one_or_none.assert_called_once()
    
    def test_get_nonexistent_task(self):
        """Test getting a task that doesn't exist or isn't owned by user."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        db_mock.execute.return_value = mock_result
        
        # Execute
        result = get_task_owned(db_mock, user_id, task_id)
        
        # Verify
        assert result is None
        db_mock.execute.assert_called_once()
        mock_result.scalar_one_or_none.assert_called_once()


class TestListTasks:
    """Test list_tasks function."""
    
    def test_list_tasks_no_status_filter(self):
        """Test listing tasks without status filter."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        
        mock_task1 = Mock(spec=Task)
        mock_task1.id = uuid.uuid4()
        mock_task1.task_description = "Task 1"
        mock_task1.status = "active"
        
        mock_task2 = Mock(spec=Task)
        mock_task2.id = uuid.uuid4()
        mock_task2.task_description = "Task 2" 
        mock_task2.status = "completed"
        
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_task1, mock_task2]
        db_mock.execute.return_value = mock_result
        
        # Execute
        result = list_tasks(db_mock, user_id, None)
        
        # Verify
        assert len(result) == 2
        assert result[0] == mock_task1
        assert result[1] == mock_task2
        db_mock.execute.assert_called_once()
        mock_result.scalars.assert_called_once()
    
    def test_list_tasks_with_status_filter(self):
        """Test listing tasks with status filter."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        status = "active"
        
        mock_task = Mock(spec=Task)
        mock_task.id = uuid.uuid4()
        mock_task.task_description = "Active task"
        mock_task.status = "active"
        
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_task]
        db_mock.execute.return_value = mock_result
        
        # Execute
        result = list_tasks(db_mock, user_id, status)
        
        # Verify
        assert len(result) == 1
        assert result[0] == mock_task
        db_mock.execute.assert_called_once()
        mock_result.scalars.assert_called_once()
    
    def test_list_tasks_with_custom_limit(self):
        """Test listing tasks with custom limit."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        limit = 5
        
        # Create mock tasks
        mock_tasks = []
        for i in range(5):
            mock_task = Mock(spec=Task)
            mock_task.id = uuid.uuid4()
            mock_task.task_description = f"Task {i+1}"
            mock_task.status = "active"
            mock_tasks.append(mock_task)
        
        mock_result = Mock()
        mock_result.scalars.return_value = mock_tasks
        db_mock.execute.return_value = mock_result
        
        # Execute
        result = list_tasks(db_mock, user_id, None, limit)
        
        # Verify
        assert len(result) == 5
        for i in range(5):
            assert result[i] == mock_tasks[i]
        db_mock.execute.assert_called_once()
        mock_result.scalars.assert_called_once()
    
    def test_list_tasks_empty_result(self):
        """Test listing tasks when no tasks exist."""
        # Setup
        db_mock = Mock()
        user_id = uuid.uuid4()
        
        mock_result = Mock()
        mock_result.scalars.return_value = []
        db_mock.execute.return_value = mock_result
        
        # Execute
        result = list_tasks(db_mock, user_id, None)
        
        # Verify
        assert len(result) == 0
        assert result == []
        db_mock.execute.assert_called_once()
        mock_result.scalars.assert_called_once()