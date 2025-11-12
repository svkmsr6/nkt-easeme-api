import httpx
from functools import lru_cache
from jose import jwt
from jose.exceptions import JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Any, Dict
from app.core.config import settings

bearer = HTTPBearer(auto_error=False)

@lru_cache(maxsize=1)
def _get_jwks():
    try:
        # Try with different headers that Supabase might expect
        headers = {
            'User-Agent': 'nkt-easeme-api/1.0',
            'apikey': settings.SUPABASE_ANON_KEY
        }
        r = httpx.get(settings.SUPABASE_JWKS_URL, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=503, 
                detail="Supabase JWKS endpoint returned 401. Check your Supabase project settings or use a different auth method."
            ) from e
        raise HTTPException(status_code=503, detail=f"Failed to fetch JWKS: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch JWKS: {str(e)}") from e

def _get_key(token: str):
    jwks = _get_jwks()
    headers = jwt.get_unverified_header(token)
    for key in jwks["keys"]:
        if key["kid"] == headers["kid"]:
            return key
    raise HTTPException(status_code=401, detail="Invalid token key id")

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> Dict[str, Any]:
    # Development bypass - remove this in production!
    if settings.APP_ENV == "dev" and (not creds or creds.credentials == "dev-bypass"):
        return {"user_id": "00000000-0000-0000-0000-000000000000"}  # Test user ID
    
    if not creds or not creds.scheme.lower() == "bearer":
        raise HTTPException(status_code=401, detail="Missing Authorization")
    
    token = creds.credentials
    
    try:
        key = _get_key(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={"verify_at_hash": False},
        )
        # supabase uid lives under 'sub'
        return {"user_id": payload.get("sub")}
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}") from e
