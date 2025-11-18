from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import logging
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)

# Use the DATABASE_URL directly from environment with proper parameter handling
_db_url = str(settings.DATABASE_URL)

# Handle asyncpg parameter compatibility
try:
    parsed = urlparse(_db_url)
    query_params = parse_qs(parsed.query)
    
    # Replace connect_timeout with command_timeout for asyncpg
    if 'connect_timeout' in query_params:
        timeout_value = query_params.pop('connect_timeout')[0]  # Get first value
        query_params['command_timeout'] = [timeout_value]
        logger.info(f"Replaced connect_timeout={timeout_value} with command_timeout={timeout_value}")
        
        # Rebuild URL with updated parameters
        new_query = urlencode(query_params, doseq=True)
        _db_url = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
        logger.info("Updated DATABASE_URL with asyncpg compatible parameters")
    
except Exception as e:
    logger.warning(f"Could not parse DATABASE_URL parameters: {e}")
    # Fallback: use original URL if parsing fails

# Simple engine configuration
engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    """
    Dependency that provides a database session.
    """
    async with SessionLocal() as session:
        # Set the search_path to use the app schema by default
        from sqlalchemy import text
        await session.execute(text("SET search_path TO app, public"))
        yield session
