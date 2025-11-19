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
    """Detailed database connectivity test with comprehensive diagnostics"""
    from urllib.parse import urlparse
    from app.core.config import settings
    import os
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": {},
        "environment": {
            "app_env": settings.APP_ENV,
            "render_service": os.environ.get("RENDER_SERVICE_NAME", "not-set"),
            "render_region": os.environ.get("RENDER_REGION", "not-set"),
        }
    }
    
    # Parse database URL
    try:
        parsed_url = urlparse(str(settings.DATABASE_URL))
        host = parsed_url.hostname
        port = parsed_url.port or 5432
        result["database_config"] = {
            "host": host,
            "port": port,
            "scheme": parsed_url.scheme,
            "username": parsed_url.username,
            "database": parsed_url.path.lstrip('/') if parsed_url.path else None
        }
    except Exception as e:
        result["database_config"] = {"error": str(e)}
        return result
    # Test DNS resolution for database host
    try:
        import socket
        # Try multiple DNS resolution methods
        try:
            ip = socket.gethostbyname(host)
            result["tests"]["dns_resolution"] = {"status": "success", "ip": ip, "method": "gethostbyname"}
        except socket.gaierror as e:
            # Try getaddrinfo as fallback
            try:
                addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
                ips = [addr[4][0] for addr in addr_info]
                result["tests"]["dns_resolution"] = {
                    "status": "success", 
                    "ips": ips, 
                    "method": "getaddrinfo",
                    "fallback_used": True
                }
            except socket.gaierror as e2:
                result["tests"]["dns_resolution"] = {
                    "status": "failed", 
                    "error": str(e),
                    "fallback_error": str(e2),
                    "suggestion": "Check if the database hostname is correct and the service is running"
                }
    except Exception as e:
        result["tests"]["dns_resolution"] = {"status": "failed", "error": str(e)}
    
    # Test TCP connectivity to database port
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        # Only test TCP if DNS resolution was successful
        if result["tests"]["dns_resolution"]["status"] == "success":
            if "ip" in result["tests"]["dns_resolution"]:
                target_ip = result["tests"]["dns_resolution"]["ip"]
            elif "ips" in result["tests"]["dns_resolution"]:
                target_ip = result["tests"]["dns_resolution"]["ips"][0]
            else:
                raise Exception("No IP address available from DNS resolution")
                
            result_code = sock.connect_ex((target_ip, port))
            sock.close()
            
            if result_code == 0:
                result["tests"]["tcp_connectivity"] = {
                    "status": "success", 
                    "port_open": True,
                    "target_ip": target_ip
                }
            else:
                result["tests"]["tcp_connectivity"] = {
                    "status": "failed", 
                    "port_open": False,
                    "error_code": result_code,
                    "target_ip": target_ip,
                    "suggestion": f"Port {port} is not accessible on {target_ip}"
                }
        else:
            result["tests"]["tcp_connectivity"] = {
                "status": "skipped",
                "reason": "DNS resolution failed, cannot test TCP connectivity"
            }
            
    except Exception as e:
        result["tests"]["tcp_connectivity"] = {"status": "failed", "error": str(e)}
    
    # Test actual database connection
    try:
        from app.db.session import engine
        
        # Only test database connection if TCP connectivity passed
        if (result["tests"].get("tcp_connectivity", {}).get("status") == "success" or 
            result["tests"].get("dns_resolution", {}).get("status") == "success"):
            
            # Use a shorter timeout for database connection test
            import asyncio
            try:
                async with asyncio.wait_for(engine.begin(), timeout=15.0) as conn:
                    db_result = await conn.execute(text("SELECT version()"))
                    version = db_result.scalar()
                    result["tests"]["database_connection"] = {
                        "status": "success",
                        "postgres_version": version[:100] if version else "unknown"
                    }
            except asyncio.TimeoutError:
                result["tests"]["database_connection"] = {
                    "status": "failed",
                    "error": "Connection timeout after 15 seconds",
                    "suggestion": "Database server may be overloaded or network is slow"
                }
        else:
            result["tests"]["database_connection"] = {
                "status": "skipped",
                "reason": "Network connectivity failed, cannot test database connection"
            }
            
    except Exception as e:
        error_msg = str(e)
        suggestions = []
        
        if "Network is unreachable" in error_msg:
            suggestions.append("Check network connectivity and firewall settings")
        if "timeout" in error_msg.lower():
            suggestions.append("Database server may be slow to respond or overloaded")
        if "authentication" in error_msg.lower() or "password" in error_msg.lower():
            suggestions.append("Check database credentials in DATABASE_URL")
        if "does not exist" in error_msg.lower():
            suggestions.append("Check database name in DATABASE_URL")
            
        result["tests"]["database_connection"] = {
            "status": "failed",
            "error": error_msg,
            "suggestions": suggestions if suggestions else ["Check DATABASE_URL configuration"]
        }
    
    # Add summary and recommendations
    all_tests = list(result["tests"].values())
    success_count = sum(1 for test in all_tests if test.get("status") == "success")
    total_tests = len([test for test in all_tests if test.get("status") != "skipped"])
    
    result["summary"] = {
        "overall_status": "healthy" if success_count == total_tests else "unhealthy",
        "tests_passed": success_count,
        "total_tests": total_tests,
        "success_rate": f"{(success_count/total_tests*100):.1f}%" if total_tests > 0 else "0%"
    }
    
    # Add troubleshooting recommendations
    if result["summary"]["overall_status"] == "unhealthy":
        recommendations = []
        
        if result["tests"].get("dns_resolution", {}).get("status") == "failed":
            recommendations.append("Verify the database hostname is correct")
            recommendations.append("Check if the Supabase project is active and not paused")
            recommendations.append("Test DNS resolution from the deployment environment")
        
        if result["tests"].get("tcp_connectivity", {}).get("status") == "failed":
            recommendations.append("Check firewall and network security group settings")
            recommendations.append("Verify the database port is correct (usually 5432 or 6543 for Supabase)")
        
        if result["tests"].get("database_connection", {}).get("status") == "failed":
            recommendations.append("Verify DATABASE_URL environment variable is set correctly")
            recommendations.append("Check database credentials and permissions")
        
        result["troubleshooting"] = {
            "recommendations": recommendations,
            "next_steps": [
                "Check Render environment variables configuration",
                "Verify Supabase project status and settings",
                "Test connectivity using /health/network endpoint"
            ]
        }
    
    return result

@router.get("/health/supabase")
async def health_supabase():
    """Specific diagnostics for Supabase database connectivity"""
    from urllib.parse import urlparse
    from app.core.config import settings
    import httpx
    import socket
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "supabase_diagnostics": {}
    }
    
    try:
        # Extract Supabase project details from DATABASE_URL
        parsed_url = urlparse(str(settings.DATABASE_URL))
        host = parsed_url.hostname
        
        if not host or not host.endswith('.supabase.co'):
            result["supabase_diagnostics"]["project_detection"] = {
                "status": "failed",
                "error": "DATABASE_URL does not appear to be a Supabase URL",
                "hostname": host
            }
            return result
        
        # Extract project ID
        project_id = host.split('.')[0]
        result["supabase_diagnostics"]["project_detection"] = {
            "status": "success",
            "project_id": project_id,
            "hostname": host
        }
        
        # Test Supabase API endpoint
        api_url = f"https://{project_id}.supabase.co"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(api_url)
                result["supabase_diagnostics"]["api_endpoint"] = {
                    "status": "success",
                    "status_code": response.status_code,
                    "url": api_url
                }
        except Exception as e:
            result["supabase_diagnostics"]["api_endpoint"] = {
                "status": "failed",
                "error": str(e),
                "url": api_url
            }
        
        # Test database hostname DNS resolution
        try:
            ip = socket.gethostbyname(host)
            result["supabase_diagnostics"]["database_dns"] = {
                "status": "success",
                "ip": ip,
                "hostname": host
            }
        except Exception as e:
            result["supabase_diagnostics"]["database_dns"] = {
                "status": "failed",
                "error": str(e),
                "hostname": host
            }
        
        # Test if project might be paused
        if result["supabase_diagnostics"]["api_endpoint"]["status"] == "failed" and \
           result["supabase_diagnostics"]["database_dns"]["status"] == "failed":
            result["supabase_diagnostics"]["project_status_warning"] = {
                "possible_issue": "Project may be paused or suspended",
                "recommendation": "Check Supabase dashboard for project status",
                "dashboard_url": f"https://supabase.com/dashboard/project/{project_id}"
            }
        
    except Exception as e:
        result["supabase_diagnostics"]["error"] = str(e)
    
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
