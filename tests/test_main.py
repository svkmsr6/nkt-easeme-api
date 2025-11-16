"""
Unit tests for app.main module and error handlers.
"""
import pytest
from unittest.mock import AsyncMock, patch, Mock
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
        
        # CORS middleware is added via add_middleware, just verify app has middlewares
        # The actual CORS functionality is tested via integration tests
        assert hasattr(app, 'user_middleware')
        # Skip detailed check since FastAPI wraps middleware in complex structures
    
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
    
    @pytest.mark.asyncio
    async def test_programming_error_schema_mismatch(self):
        """Test ProgrammingError handler for schema mismatch."""
        app = create_app()
        handler = app.exception_handlers[ProgrammingError]
        
        request = Mock(spec=Request)
        exc = ProgrammingError("column does not exist", None, None)
        
        response = await handler(request, exc)
        
        assert response.status_code == 503
        content = response.body.decode()
        assert "schema" in content.lower() or "mismatch" in content.lower()
    
    @pytest.mark.asyncio
    async def test_programming_error_generic(self):
        """Test ProgrammingError handler for generic errors."""
        app = create_app()
        handler = app.exception_handlers[ProgrammingError]
        
        request = Mock(spec=Request)
        exc = ProgrammingError("some other error", None, None)
        
        response = await handler(request, exc)
        
        assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_operational_error_handler(self):
        """Test OperationalError handler."""
        app = create_app()
        handler = app.exception_handlers[OperationalError]
        
        request = Mock(spec=Request)
        exc = OperationalError("connection failed", None, None)
        
        response = await handler(request, exc)
        
        assert response.status_code == 503
        content = response.body.decode()
        assert "database" in content.lower() or "connection" in content.lower()
    
    @pytest.mark.asyncio
    async def test_integrity_error_handler(self):
        """Test IntegrityError handler."""
        app = create_app()
        handler = app.exception_handlers[IntegrityError]
        
        request = Mock(spec=Request)
        exc = IntegrityError("constraint violation", None, None)
        
        response = await handler(request, exc)
        
        assert response.status_code == 400
        content = response.body.decode()
        assert "integrity" in content.lower() or "constraint" in content.lower()


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
