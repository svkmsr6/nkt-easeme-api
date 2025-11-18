from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
from app.db.session import get_db
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint that verifies both API and database connectivity.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "unknown"
    }
    
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        health_status["database"] = "connected"
        logger.info("Database health check successful")
    except Exception as e:
        logger.error("Database health check failed: %s", str(e))
        health_status["status"] = "unhealthy"
        health_status["database"] = "disconnected"
        health_status["error"] = str(e)
    
    return health_status

@router.get("/health/simple")
async def health_simple():
    """Simple health check without database dependency"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "API is running"
    }

@router.get("/health/debug")
async def health_debug():
    """Debug endpoint to check database URL configuration"""
    db_url = str(settings.DATABASE_URL)
    # Mask password for security
    if '@' in db_url:
        parts = db_url.split('@')
        user_pass = parts[0].split('://')[-1]
        if ':' in user_pass:
            user, password = user_pass.split(':', 1)
            masked_url = db_url.replace(password, '***')
        else:
            masked_url = db_url
    else:
        masked_url = db_url
    
    return {
        "database_url": masked_url,
        "app_env": settings.APP_ENV,
        "render_service": os.environ.get("RENDER_SERVICE_NAME", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
