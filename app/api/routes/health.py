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
    from app.db import session as db_session
    
    # Get the original URL from settings
    original_url = str(settings.DATABASE_URL)
    
    # Try to get the cleaned URL that's actually being used
    # This requires accessing the engine's URL
    try:
        engine_url = str(db_session.engine.url)
    except:
        engine_url = "Unable to retrieve engine URL"
    
    # Mask passwords for security
    def mask_password(url):
        if '@' in url:
            parts = url.split('@')
            user_pass = parts[0].split('://')[-1]
            if ':' in user_pass:
                user, password = user_pass.split(':', 1)
                return url.replace(password, '***')
        return url
    
    return {
        "original_database_url": mask_password(original_url),
        "engine_database_url": mask_password(engine_url),
        "app_env": settings.APP_ENV,
        "render_service": os.environ.get("RENDER_SERVICE_NAME", "unknown"),
        "render_region": os.environ.get("RENDER_REGION", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/health/network")
async def health_network():
    """Test network connectivity to various endpoints"""
    import asyncio
    import socket
    import httpx
    
    results = {}
    
    # Test DNS resolution
    try:
        import socket
        host = "db.trjevaajfqwleetrmncz.supabase.co"
        ip = socket.gethostbyname(host)
        results["dns_resolution"] = {"status": "success", "ip": ip}
    except Exception as e:
        results["dns_resolution"] = {"status": "failed", "error": str(e)}
    
    # Test HTTP connectivity to Supabase
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://trjevaajfqwleetrmncz.supabase.co")
            results["supabase_http"] = {
                "status": "success", 
                "status_code": response.status_code,
                "reachable": True
            }
    except Exception as e:
        results["supabase_http"] = {"status": "failed", "error": str(e)}
    
    # Test external connectivity
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("https://httpbin.org/ip")
            ip_info = response.json()
            results["external_connectivity"] = {
                "status": "success",
                "outbound_ip": ip_info.get("origin", "unknown")
            }
    except Exception as e:
        results["external_connectivity"] = {"status": "failed", "error": str(e)}
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network_tests": results
    }
