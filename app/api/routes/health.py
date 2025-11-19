'''
Provides various levels of health checks including simple API status,
full API and database connectivity, and detailed database tests.
'''
import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

@router.get("/health")
async def health():
    """
    Simple health check endpoint for Render deployment checks.
    Does not require database connectivity.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "API is running",
        "service": "nkt-easeme-api"
    }

@router.get("/health/full")
async def health_full(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check endpoint that verifies both API and database connectivity.
    Use this for detailed application health monitoring.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "unknown",
        "service": "nkt-easeme-api"
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

@router.get("/health/database")
async def health_database():
    """Detailed database connectivity test"""
    from urllib.parse import urlparse
    from app.core.config import settings
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": {}
    }
    
    # Parse database URL
    try:
        parsed_url = urlparse(str(settings.DATABASE_URL))
        host = parsed_url.hostname
        port = parsed_url.port or 5432
        result["database_config"] = {
            "host": host,
            "port": port,
            "scheme": parsed_url.scheme
        }
    except Exception as e:
        result["database_config"] = {"error": str(e)}
        return result
    # Test DNS resolution for database host
    try:
        import socket
        ip = socket.gethostbyname(host)
        result["tests"]["dns_resolution"] = {"status": "success", "ip": ip}
    except Exception as e:
        result["tests"]["dns_resolution"] = {"status": "failed", "error": str(e)}
    
    # Test TCP connectivity to database port
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result_code = sock.connect_ex((host, port))
        sock.close()
        
        if result_code == 0:
            result["tests"]["tcp_connectivity"] = {"status": "success", "port_open": True}
        else:
            result["tests"]["tcp_connectivity"] = {
                "status": "failed", 
                "port_open": False,
                "error_code": result_code
            }
    except Exception as e:
        result["tests"]["tcp_connectivity"] = {"status": "failed", "error": str(e)}
    
    # Test actual database connection
    try:
        from app.db.session import engine
        async with engine.begin() as conn:
            db_result = await conn.execute(text("SELECT version()"))
            version = db_result.scalar()
            result["tests"]["database_connection"] = {
                "status": "success",
                "postgres_version": version[:50] if version else "unknown"
            }
    except Exception as e:
        result["tests"]["database_connection"] = {"status": "failed", "error": str(e)}
    
    return result

@router.get("/health/network")
async def health_network():
    """Test network connectivity to various endpoints"""
    import asyncio
    import socket
    import httpx
    from urllib.parse import urlparse
    from app.core.config import settings
    
    results = {}
    
    # Get the actual database hostname from settings
    try:
        parsed_url = urlparse(str(settings.DATABASE_URL))
        db_host = parsed_url.hostname
        supabase_project = db_host.split('.')[0] if db_host else None
        results["database_config"] = {
            "hostname": db_host,
            "project_id": supabase_project
        }
    except Exception as e:
        results["database_config"] = {"error": str(e)}
        db_host = None
        supabase_project = None
    
    # Test DNS resolution for actual database host
    if db_host:
        try:
            ip = socket.gethostbyname(db_host)
            results["dns_resolution"] = {"status": "success", "ip": ip, "hostname": db_host}
        except Exception as e:
            results["dns_resolution"] = {"status": "failed", "error": str(e), "hostname": db_host}
    else:
        results["dns_resolution"] = {"status": "failed", "error": "Could not extract hostname from DATABASE_URL"}
    
    # Test HTTP connectivity to Supabase project
    if supabase_project:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"https://{supabase_project}.supabase.co")
                results["supabase_http"] = {
                    "status": "success", 
                    "status_code": response.status_code,
                    "reachable": True,
                    "url": f"https://{supabase_project}.supabase.co"
                }
        except Exception as e:
            results["supabase_http"] = {
                "status": "failed", 
                "error": str(e),
                "url": f"https://{supabase_project}.supabase.co"
            }
    
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
