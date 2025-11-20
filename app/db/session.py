
import logging
from urllib.parse import urlparse, parse_qs, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

# Use the DATABASE_URL directly from environment with proper parameter handling
_db_url = str(settings.DATABASE_URL)
logger.info(f"Original DATABASE_URL: {_db_url[:50]}...")  # Log first 50 chars for debugging

# Parse URL properly to handle parameters correctly and force IPv4 if needed
try:
    parsed = urlparse(_db_url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Handle parameter replacements and removals
    params_modified = False
    hostname_modified = False
    
    # Try to resolve hostname to IPv4 to avoid IPv6 issues in some cloud environments
    original_hostname = parsed.hostname
    try:
        import socket
        # Try to get IPv4 address specifically
        ipv4_addresses = []
        try:
            # Get all address info and filter for IPv4
            addr_info = socket.getaddrinfo(original_hostname, None, socket.AF_INET, socket.SOCK_STREAM)
            ipv4_addresses = [addr[4][0] for addr in addr_info]
        except socket.gaierror:
            # Fallback to gethostbyname which should return IPv4
            ipv4_addresses = [socket.gethostbyname(original_hostname)]
        
        if ipv4_addresses:
            # Use the first IPv4 address found
            ipv4_address = ipv4_addresses[0]
            logger.info(f"Resolved {original_hostname} to IPv4: {ipv4_address}")
            
            # Replace hostname with IPv4 address in the URL
            new_netloc = parsed.netloc.replace(original_hostname, ipv4_address)
            hostname_modified = True
        else:
            logger.warning(f"Could not resolve {original_hostname} to IPv4, using original hostname")
            new_netloc = parsed.netloc
            
    except Exception as dns_error:
        logger.warning(f"Could not resolve hostname to IPv4: {dns_error}, using original hostname")
        new_netloc = parsed.netloc
    
    # Replace connect_timeout with command_timeout
    if 'connect_timeout' in query_params:
        timeout_value = query_params.pop('connect_timeout')[0]  # Get first value as string
        query_params['command_timeout'] = [str(timeout_value)]  # Ensure it's a string
        params_modified = True
        logger.info(f"Replaced connect_timeout={timeout_value} with command_timeout={timeout_value}")
    
    # Remove problematic parameters that asyncpg doesn't support
    problematic_params = ['server_settings', 'passfile', 'channel_binding', 'gssencmode']
    for param in problematic_params:
        if param in query_params:
            del query_params[param]
            params_modified = True
            logger.info(f"Removed unsupported parameter: {param}")

    # Ensure command_timeout is a single string value, not a list
    if 'command_timeout' in query_params:
        if isinstance(query_params['command_timeout'], list):
            query_params['command_timeout'] = [str(query_params['command_timeout'][0])]
        else:
            query_params['command_timeout'] = [str(query_params['command_timeout'])]

    # Rebuild URL if we modified parameters or hostname
    if params_modified or hostname_modified:
        # Convert all parameter values to strings and flatten lists to single values
        clean_params = {}
        for key, value_list in query_params.items():
            if isinstance(value_list, list) and len(value_list) > 0:
                clean_params[key] = str(value_list[0])  # Take first value and ensure it's string
            else:
                clean_params[key] = str(value_list) if value_list else ''

        # Rebuild query string manually to avoid list issues
        query_parts = []
        for key, value in clean_params.items():
            query_parts.append(f"{key}={value}")
        new_query = '&'.join(query_parts)

        _db_url = urlunparse((
            parsed.scheme, 
            new_netloc if hostname_modified else parsed.netloc, 
            parsed.path,
            parsed.params, 
            new_query, 
            parsed.fragment
        ))

        if hostname_modified:
            logger.info("Updated DATABASE_URL with IPv4 address")
        if params_modified:
            logger.info("Updated DATABASE_URL with asyncpg compatible parameters")

    logger.info(f"Final DATABASE_URL: {_db_url[:50]}...")  # Log first 50 chars for debugging

except Exception as e:
    logger.error(f"Could not parse DATABASE_URL parameters: {e}")
    # Fallback: use original URL if parsing fails
    logger.info(f"Using original DATABASE_URL: {_db_url[:50]}...")

# Simple engine configuration with better error handling and network resilience
engine = create_engine(
    _db_url,
    poolclass=NullPool,
    pool_pre_ping=True,
    pool_recycle=1800,  # Recycle connections every 30 minutes (shorter for cloud environments)
    echo=False,
    connect_args={}
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def test_db_connection():
    """
    Simple database connection test that returns True/False without raising exceptions.
    Useful for health checks where you want to test connectivity without failing the endpoint.
    """
    try:
        async with SessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

async def get_db():
    """
    Dependency that provides a database session with retry logic and better error handling.
    """
    import asyncio
    
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            async with SessionLocal() as session:
                # Set the search_path to use the app schema by default
                from sqlalchemy import text
                await session.execute(text("SET search_path TO app, public"))
                yield session
                return  # Success, exit the retry loop
                
        except OSError as e:
            error_msg = str(e)
            if any(error_type in error_msg for error_type in [
                "Network is unreachable", 
                "Connection refused", 
                "No address associated with hostname",
                "Temporary failure in name resolution",
                "timeout"
            ]):
                if attempt < max_retries - 1:
                    logger.warning(f"Network/connection issue, attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay}s... Error: {e}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                    # Provide more helpful error message for deployment
                    deployment_error = (
                        f"Database connection failed after {max_retries} attempts. "
                        f"This usually indicates a network connectivity issue or incorrect database configuration. "
                        f"Last error: {e}. "
                        f"Check DATABASE_URL environment variable and network connectivity."
                    )
                    raise OSError(deployment_error) from e
            else:
                logger.error(f"Database connection failed with non-retryable OSError: {e}")
                raise
                
        except Exception as e:
            # For other exceptions, don't retry - they might be application-level issues
            if attempt == 0:  # Only log once for non-Exception exceptions
                logger.error(f"Database session error (non-retryable): {e}")
            raise
