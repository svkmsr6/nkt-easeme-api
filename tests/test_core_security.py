"""
Unit tests for app.core.security module.
"""
import pytest
import uuid
from jose import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
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
        
        from fastapi.security import HTTPAuthorizationCredentials
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
            
            from fastapi.security import HTTPAuthorizationCredentials
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            
            result = await get_current_user(creds)
            
            assert result["user_id"] == user_id
            assert result["role"] == "authenticated"
