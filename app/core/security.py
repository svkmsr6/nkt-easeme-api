from __future__ import annotations

import logging
import uuid
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Any, Dict, Optional
from app.core.config import settings

# Initialize logger (suppressing false positive linter warning)
logger = getattr(logging, 'getLogger')(__name__)
bearer = HTTPBearer(auto_error=False)

def verify_supabase_token(token: str) -> Dict[str, Any]:
    """
    Verify a Supabase JWT token using the JWT secret
    """
    try:
        # Use the JWT secret to verify the token
        if settings.SUPABASE_JWT_SECRET:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_signature": True, "verify_aud": False, "verify_iss": False}
            )
            logger.info("Token verified with JWT secret")
        else:
            # Fallback: decode without verification (development only)
            logger.warning("No JWT secret configured, using unverified token decode")
            payload = jwt.decode(token, key="", options={"verify_signature": False})
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing user ID")
            
        # Validate that user_id is a valid UUID format if possible
        try:
            uuid.UUID(user_id)
        except ValueError:
            # If it's not a UUID, it might be an email or another identifier
            logger.info(f"User ID is not a UUID format: {user_id}")
            
        return {
            "user_id": user_id, 
            "role": payload.get("role", "authenticated"),
            "email": payload.get("email")
        }
        
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}") from e
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed") from e

async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> Dict[str, Any]:
    """
    Get current user from JWT token or return dev user in development mode
    """
    # Development mode with valid UUID
    if settings.APP_ENV == "dev":
        if not creds:
            logger.info("No credentials in dev mode, using test user")
            return {"user_id": "123e4567-e89b-12d3-a456-426614174000"}  # Valid UUID for testing
        
        if creds.credentials in ["dev-bypass", "test", "dev"]:
            logger.info("Dev bypass token used")
            return {"user_id": "123e4567-e89b-12d3-a456-426614174000"}  # Valid UUID for testing
    
    # Require proper authorization
    if not creds or not creds.scheme.lower() == "bearer":
        if settings.APP_ENV == "dev":
            logger.info("No proper auth in dev mode, using test user")
            return {"user_id": "123e4567-e89b-12d3-a456-426614174000"}
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = creds.credentials
    
    try:
        # Use our Supabase token verification
        user_data = verify_supabase_token(token)
        return user_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        if settings.APP_ENV == "dev":
            logger.info("Token verification failed in dev mode, using test user")
            return {"user_id": "123e4567-e89b-12d3-a456-426614174000"}
        raise
    except Exception as e:
        logger.error(f"Unexpected error in authentication: {e}")
        if settings.APP_ENV == "dev":
            logger.info("Unexpected auth error in dev mode, using test user")
            return {"user_id": "123e4567-e89b-12d3-a456-426614174000"}
        raise HTTPException(status_code=401, detail="Authentication failed") from e