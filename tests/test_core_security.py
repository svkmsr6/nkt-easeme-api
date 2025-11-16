"""
Unit tests for app.core.security module.
"""
import pytest
import uuid
from jose import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.core.security import verify_supabase_token, get_current_user
from app.core.config import settings


class TestVerifySupabaseToken:
    """Test Supabase token verification."""
    
    def test_verify_token_with_secret(self):
        """Test token verification with JWT secret."""
        user_id = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "role": "authenticated",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        if settings.SUPABASE_JWT_SECRET:
            token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
            result = verify_supabase_token(token)
            
            assert result["user_id"] == user_id
            assert result["role"] == "authenticated"
            assert result["email"] == "test@example.com"
    
    def test_verify_token_without_secret(self, monkeypatch):
        """Test token verification without JWT secret (fallback mode)."""
        monkeypatch.setattr("app.core.security.settings.SUPABASE_JWT_SECRET", None)
        
        user_id = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "role": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        # Create token without signature
        token = jwt.encode(payload, "", algorithm="HS256")
        result = verify_supabase_token(token)
        
        assert result["user_id"] == user_id
        assert result["role"] == "authenticated"
    
    def test_verify_token_expired(self):
        """Test that expired tokens are rejected."""
        user_id = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "role": "authenticated",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1)
        }
        
        if settings.SUPABASE_JWT_SECRET:
            token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
            
            with pytest.raises(HTTPException) as exc_info:
                verify_supabase_token(token)
            
            assert exc_info.value.status_code == 401
            assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_token_missing_user_id(self):
        """Test token without user ID is rejected."""
        payload = {
            "role": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        if settings.SUPABASE_JWT_SECRET:
            token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
            
            with pytest.raises(HTTPException) as exc_info:
                verify_supabase_token(token)
            
            assert exc_info.value.status_code == 401
            detail_lower = exc_info.value.detail.lower()
            # Either error message is acceptable
            assert "missing user id" in detail_lower or "verification failed" in detail_lower
    
    def test_verify_invalid_token(self):
        """Test that invalid tokens are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_token_validates_uuid(self):
        """Test token with valid UUID format."""
        user_id = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        if settings.SUPABASE_JWT_SECRET:
            token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
            result = verify_supabase_token(token)
            
            # Should successfully parse as UUID
            assert uuid.UUID(result["user_id"]) == uuid.UUID(user_id)
    
    def test_verify_token_non_uuid_user_id(self):
        """Test token with non-UUID user ID (like email)."""
        payload = {
            "sub": "user@example.com",  # Non-UUID format
            "role": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        if settings.SUPABASE_JWT_SECRET:
            token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
            result = verify_supabase_token(token)
            
            # Should still work even with non-UUID format
            assert result["user_id"] == "user@example.com"


class TestGetCurrentUser:
    """Test get_current_user dependency."""
    
    @pytest.mark.asyncio
    async def test_dev_mode_no_credentials(self, monkeypatch):
        """Test dev mode allows requests without credentials."""
        monkeypatch.setattr("app.core.security.settings.APP_ENV", "dev")
        
        result = await get_current_user(None)
        
        assert "user_id" in result
        assert isinstance(uuid.UUID(result["user_id"]), uuid.UUID)
    
    @pytest.mark.asyncio
    async def test_dev_bypass_token(self, monkeypatch):
        """Test dev bypass tokens work in dev mode."""
        monkeypatch.setattr("app.core.security.settings.APP_ENV", "dev")
        
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dev-bypass")
        
        result = await get_current_user(creds)
        
        assert "user_id" in result
    
    @pytest.mark.asyncio
    async def test_production_requires_auth(self, monkeypatch):
        """Test production mode requires proper authentication."""
        monkeypatch.setattr("app.core.security.settings.APP_ENV", "production")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_valid_token_authentication(self, monkeypatch):
        """Test authentication with valid token."""
        user_id = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "role": "authenticated",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        if settings.SUPABASE_JWT_SECRET:
            token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
            
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            
            result = await get_current_user(creds)
            
            assert result["user_id"] == user_id
            assert result["role"] == "authenticated"
    
    @pytest.mark.asyncio
    async def test_non_bearer_scheme_in_production(self, monkeypatch):
        """Test that non-Bearer scheme fails in production."""
        monkeypatch.setattr("app.core.security.settings.APP_ENV", "production")
        
        creds = HTTPAuthorizationCredentials(scheme="Basic", credentials="test")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_token_in_dev_mode(self, monkeypatch):
        """Test that invalid token in dev mode falls back to test user."""
        monkeypatch.setattr("app.core.security.settings.APP_ENV", "dev")
        
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token")
        
        result = await get_current_user(creds)
        
        # Should fallback to test user in dev mode
        assert "user_id" in result
    
    @pytest.mark.asyncio
    async def test_exception_during_auth_in_dev(self, monkeypatch):
        """Test that exceptions during auth in dev mode return test user."""
        monkeypatch.setattr("app.core.security.settings.APP_ENV", "dev")
        
        # Use a malformed token that causes an exception
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="definitely_not_a_token")
        
        result = await get_current_user(creds)
        
        # Should fallback to test user
        assert "user_id" in result
    
    @pytest.mark.asyncio
    async def test_exception_during_auth_in_production(self, monkeypatch):
        """Test that exceptions during auth in production raise HTTPException."""
        monkeypatch.setattr("app.core.security.settings.APP_ENV", "production")
        
        # Use a malformed token that causes an exception
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="definitely_not_a_token")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_non_bearer_scheme_in_dev(self, monkeypatch):
        """Test that non-Bearer scheme in dev mode returns test user."""
        monkeypatch.setattr("app.core.security.settings.APP_ENV", "dev")
        
        creds = HTTPAuthorizationCredentials(scheme="Basic", credentials="test")
        
        result = await get_current_user(creds)
        
        # Should fallback to test user in dev mode
        assert "user_id" in result
