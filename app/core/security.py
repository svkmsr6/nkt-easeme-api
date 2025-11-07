import httpx
from functools import lru_cache
from jose import jwt
from jose.exceptions import JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Any, Dict
from app.core.config import settings

bearer = HTTPBearer(auto_error=False)

@lru_cache(maxsize=1)
def _get_jwks():
    r = httpx.get(settings.SUPABASE_JWKS_URL, timeout=10)
    r.raise_for_status()
    return r.json()

def _get_key(token: str):
    jwks = _get_jwks()
    headers = jwt.get_unverified_header(token)
    for key in jwks["keys"]:
        if key["kid"] == headers["kid"]:
            return key
    raise HTTPException(status_code=401, detail="Invalid token key id")

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> Dict[str, Any]:
    if not creds or not creds.scheme.lower() == "bearer":
        raise HTTPException(status_code=401, detail="Missing Authorization")
    token = creds.credentials
    key = _get_key(token)
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={"verify_at_hash": False},
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    # supabase uid lives under 'sub'
    return {"user_id": payload.get("sub")}
