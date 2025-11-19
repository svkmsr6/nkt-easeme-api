from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import logging
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)

# Use the DATABASE_URL directly from environment with proper parameter handling
_db_url = str(settings.DATABASE_URL)
logger.info(f"Original DATABASE_URL: {_db_url[:50]}...")  # Log first 50 chars for debugging

# Parse URL properly to handle parameters correctly
try:
    parsed = urlparse(_db_url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Handle parameter replacements and removals
    params_modified = False
    
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
    
    # Rebuild URL only if we modified parameters
    if params_modified:
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
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
        logger.info("Updated DATABASE_URL with asyncpg compatible parameters")
    
    logger.info(f"Final DATABASE_URL: {_db_url[:50]}...")  # Log first 50 chars for debugging
    
except Exception as e:
    logger.error(f"Could not parse DATABASE_URL parameters: {e}")
    # Fallback: use original URL if parsing fails
    logger.info(f"Using original DATABASE_URL: {_db_url[:50]}...")

# Simple engine configuration with better error handling and network resilience
engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,
    pool_recycle=1800,  # Recycle connections every 30 minutes (shorter for cloud environments)
    pool_timeout=45,    # Wait up to 45 seconds for a connection
    max_overflow=15,    # Allow up to 15 connections beyond pool_size
    pool_size=5,        # Default connection pool size
    echo=False,
    connect_args={
        "command_timeout": 45,  # Set command timeout directly (increased for network issues)
        "server_settings": {
            "application_name": "nkt-easeme-api",
        },
        # Add connection-level settings for better network resilience
        "ssl": "require",  # Ensure SSL is used
    } if "postgresql+asyncpg" in _db_url else {}
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    """
    Dependency that provides a database session with retry logic.
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
            if "Network is unreachable" in str(e) or "Connection refused" in str(e):
                if attempt < max_retries - 1:
                    logger.warning(f"Network/connection issue, attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay}s... Error: {e}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                    raise OSError(f"Failed to connect to database after {max_retries} attempts. Last error: {e}") from e
            else:
                logger.error(f"Database connection failed with non-retryable OSError: {e}")
                raise
                
        except Exception as e:
            # For other exceptions, don't retry - they might be application-level issues
            if attempt == 0:  # Only log once for non-OSError exceptions
                logger.error(f"Database session error (non-retryable): {e}")
            raise
