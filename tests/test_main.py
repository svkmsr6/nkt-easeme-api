"""
Unit tests for app.main module and error handlers.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import Request
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError
from app.main import create_app


class TestCreateApp:
    """Test create_app function."""
    
    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        app = create_app()
        
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        assert app.title in ["EaseMe API", "NKT_EaseMe_API"]
    
    def test_app_has_cors_middleware(self):
        """Test that CORS middleware is configured."""
        app = create_app()
        
        # Check middleware is present - CORS middleware may appear differently
        has_cors = False
        if hasattr(app, 'user_middleware'):
            middleware_types = [type(m).__name__ for m in app.user_middleware]
            has_cors = 'CORSMiddleware' in middleware_types
        if not has_cors and hasattr(app, 'middleware'):
            # Check in middleware stack as well
            has_cors = any('CORS' in str(type(m)) for m in app.middleware)
        assert has_cors, "CORS middleware not found"
    
    def test_app_includes_all_routers(self):
        """Test that all routers are included."""
        app = create_app()
        
        # Check routes exist by examining route paths
        route_paths = []
        for route in app.routes:
            # Use getattr to safely access path attribute
            path = getattr(route, 'path', None)
            if path:
                route_paths.append(path)
        
        # Health route
        assert "/health" in route_paths
        
        # Task routes
        assert any("/api/tasks" in r for r in route_paths)
        
        # Intervention routes
        assert any("/api/interventions" in r for r in route_paths)
        
        # Checkin routes
        assert any("/api/checkins" in r for r in route_paths)
        
        # Dashboard route
        assert any("/api/user" in r for r in route_paths)
        
        # AI routes
        assert any("/api/ai" in r for r in route_paths)


class TestExceptionHandlers:
    """Test exception handlers."""
    
    @pytest.mark.asyncio
    async def test_exception_handlers_registered(self):
        """Test that exception handlers are registered."""
        app = create_app()
        
        # Verify exception handlers are configured
        assert ProgrammingError in app.exception_handlers
        assert OperationalError in app.exception_handlers
        assert IntegrityError in app.exception_handlers


class TestAppModule:
    """Test app module level."""
    
    def test_app_instance_created(self):
        """Test that app instance is created at module level."""
        from app.main import app
        
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
    
    def test_app_configuration(self):
        """Test app is properly configured."""
        from app.main import app
        from app.core.config import settings
        
        assert app.title == settings.APP_NAME
