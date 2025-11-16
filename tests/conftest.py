"""
Pytest configuration and shared fixtures for all tests.
"""
import asyncio
import os
import uuid
from typing import AsyncGenerator, Generator
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models import Base
from app.main import create_app


# Test database URL - use a separate test database
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", str(settings.DATABASE_URL))
if TEST_DATABASE_URL.startswith("postgresql://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Create schema if not exists
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
        await conn.execute(text("SET search_path TO app, public"))
        # Drop all tables to ensure clean state
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    SessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with SessionLocal() as session:
        # Set search path
        await session.execute(text("SET search_path TO app, public"))
        yield session
        await session.rollback()


@pytest.fixture
def test_user_id() -> uuid.UUID:
    """Generate a test user ID."""
    return uuid.UUID("123e4567-e89b-12d3-a456-426614174000")


@pytest.fixture
def another_user_id() -> uuid.UUID:
    """Generate another test user ID for multi-user tests."""
    return uuid.UUID("223e4567-e89b-12d3-a456-426614174001")


@pytest.fixture
def mock_auth_user(test_user_id):
    """Mock authenticated user."""
    return {"user_id": str(test_user_id), "role": "authenticated", "email": "test@example.com"}


@pytest.fixture
async def client(db_session, test_user_id) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with mocked authentication."""
    app = create_app()
    
    # Override database dependency
    async def override_get_db():
        yield db_session
    
    # Override auth dependency for testing
    async def override_auth():
        return {"user_id": str(test_user_id), "role": "authenticated"}
    
    from app.api.deps import Authed
    from app.db.session import get_db
    from app.core.security import get_current_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_auth
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def utc_now():
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"pattern": "perfectionism", "technique_id": "permission_protocol", "message": "Test message", "duration_seconds": 300}'
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70
        }
    }


@pytest.fixture
def mock_emotion_labels_response():
    """Mock OpenAI emotion labels response."""
    return {
        "id": "chatcmpl-test456",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"labels": ["Fear of judgment", "Perfectionism anxiety", "Performance pressure"]}'
                },
                "finish_reason": "stop"
            }
        ]
    }
