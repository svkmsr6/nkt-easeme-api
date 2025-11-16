"""
Unit tests for app.repositories.task_repo module.
"""
import pytest
import uuid
from app.repositories.task_repo import create_task, get_task_owned, list_tasks
from app.db.models import Task


class TestCreateTask:
    """Test create_task function."""
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, db_session, test_user_id):
        """Test creating a task successfully."""
        description = "Write unit tests"
        
        task = await create_task(db_session, test_user_id, description)
        
        assert task.id is not None
        assert task.user_id == test_user_id
        assert task.task_description == description
        assert task.status == "active"
        assert task.created_at is not None
    
    @pytest.mark.asyncio
    async def test_create_task_with_empty_description(self, db_session, test_user_id):
        """Test creating a task with empty description."""
        task = await create_task(db_session, test_user_id, "")
        
        assert task.task_description == ""


class TestGetTaskOwned:
    """Test get_task_owned function."""
    
    @pytest.mark.asyncio
    async def test_get_existing_task(self, db_session, test_user_id):
        """Test getting an existing task."""
        # Create a task first
        task = await create_task(db_session, test_user_id, "Test task")
        
        # Retrieve it
        result = await get_task_owned(db_session, test_user_id, task.id)
        
        assert result is not None
        assert result.id == task.id
        assert result.user_id == test_user_id
        assert result.task_description == "Test task"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, db_session, test_user_id):
        """Test getting a nonexistent task returns None."""
        fake_id = uuid.uuid4()
        
        result = await get_task_owned(db_session, test_user_id, fake_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_task_wrong_user(self, db_session, test_user_id, another_user_id):
        """Test getting a task owned by another user returns None."""
        # Create task for test_user
        task = await create_task(db_session, test_user_id, "Test task")
        
        # Try to get it with another user
        result = await get_task_owned(db_session, another_user_id, task.id)
        
        assert result is None


class TestListTasks:
    """Test list_tasks function."""
    
    @pytest.mark.asyncio
    async def test_list_all_tasks(self, db_session, test_user_id):
        """Test listing all tasks for a user."""
        # Create multiple tasks
        await create_task(db_session, test_user_id, "Task 1")
        await create_task(db_session, test_user_id, "Task 2")
        await create_task(db_session, test_user_id, "Task 3")
        
        tasks = await list_tasks(db_session, test_user_id, status=None)
        
        assert len(tasks) == 3
        assert all(t.user_id == test_user_id for t in tasks)
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, db_session, test_user_id):
        """Test listing tasks filtered by status."""
        # Create tasks with different statuses
        task1 = await create_task(db_session, test_user_id, "Active task")
        task2 = await create_task(db_session, test_user_id, "Completed task")
        task2.status = "completed"
        await db_session.commit()
        
        # List only active tasks
        active_tasks = await list_tasks(db_session, test_user_id, status="active")
        
        assert len(active_tasks) >= 1
        assert all(t.status == "active" for t in active_tasks)
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_limit(self, db_session, test_user_id):
        """Test listing tasks with limit."""
        # Create multiple tasks
        for i in range(10):
            await create_task(db_session, test_user_id, f"Task {i}")
        
        tasks = await list_tasks(db_session, test_user_id, status=None, limit=5)
        
        assert len(tasks) == 5
    
    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, db_session, test_user_id):
        """Test listing tasks when none exist."""
        tasks = await list_tasks(db_session, test_user_id, status=None)
        
        assert len(tasks) == 0
    
    @pytest.mark.asyncio
    async def test_list_tasks_ordered_by_created_at(self, db_session, test_user_id):
        """Test that tasks are ordered by created_at desc."""
        task1 = await create_task(db_session, test_user_id, "First")
        task2 = await create_task(db_session, test_user_id, "Second")
        task3 = await create_task(db_session, test_user_id, "Third")
        
        tasks = await list_tasks(db_session, test_user_id, status=None)
        
        # Should be in reverse order (newest first)
        assert tasks[0].task_description == "Third"
        assert tasks[1].task_description == "Second"
        assert tasks[2].task_description == "First"
    
    @pytest.mark.asyncio
    async def test_list_tasks_only_own_tasks(self, db_session, test_user_id, another_user_id):
        """Test that user only sees their own tasks."""
        # Create tasks for different users
        await create_task(db_session, test_user_id, "User 1 task")
        await create_task(db_session, another_user_id, "User 2 task")
        
        user1_tasks = await list_tasks(db_session, test_user_id, status=None)
        
        assert len(user1_tasks) == 1
        assert user1_tasks[0].task_description == "User 1 task"
