from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import logging
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)

# `settings.DATABASE_URL` is a Pydantic AnyUrl. SQLAlchemy expects a string or URL object.
# Convert to string to avoid: ArgumentError: Expected string or URL object, got AnyUrl(...)
_db_url = str(settings.DATABASE_URL)

# Ensure an async DB driver is specified for SQLAlchemy asyncio. If the URL is
# a plain `postgresql://...` convert it to `postgresql+asyncpg://...` so the
# asyncpg driver is used. This avoids InvalidRequestError when a sync driver
# (psycopg2) is present in the environment.
if _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Clean up URL parameters that are not compatible with asyncpg
def clean_asyncpg_url(url: str) -> str:
    """Remove URL parameters that are not compatible with asyncpg"""
    parsed = urlparse(url)
    if not parsed.query:
        return url
    
    # Parse query parameters
    params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Remove invalid parameters for asyncpg
    invalid_params = ['connect_timeout']
    for param in invalid_params:
        if param in params:
            logger.info(f"Removing invalid asyncpg parameter: {param}")
            del params[param]
    
    # Rebuild query string
    new_query = urlencode(params, doseq=True) if params else ''
    
    # Rebuild URL
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import logging
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)

# `settings.DATABASE_URL` is a Pydantic AnyUrl. SQLAlchemy expects a string or URL object.
# Convert to string to avoid: ArgumentError: Expected string or URL object, got AnyUrl(...)
_db_url = str(settings.DATABASE_URL)

# Ensure an async DB driver is specified for SQLAlchemy asyncio. If the URL is
# a plain `postgresql://...` convert it to `postgresql+asyncpg://...` so the
# asyncpg driver is used. This avoids InvalidRequestError when a sync driver
# (psycopg2) is present in the environment.
if _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Clean the database URL with multiple approaches
def robust_url_cleaning(url: str) -> str:
    """Clean URL using multiple approaches to ensure connect_timeout is removed"""
    logger.info("Starting robust URL cleaning...")
    
    # Approach 1: Simple string replacement
    cleaned_url = url
    if 'connect_timeout=' in cleaned_url:
        logger.info("Found connect_timeout parameter, removing with string replacement")
        # Remove connect_timeout parameter and its value
        import re
        cleaned_url = re.sub(r'[&?]connect_timeout=\d+', '', cleaned_url)
        cleaned_url = re.sub(r'connect_timeout=\d+[&]?', '', cleaned_url)
        
        # Clean up any double ampersands or trailing question marks
        cleaned_url = cleaned_url.replace('?&', '?').replace('&&', '&')
        if cleaned_url.endswith('?') or cleaned_url.endswith('&'):
            cleaned_url = cleaned_url[:-1]
    
    # Approach 2: Use the original URL parsing method as backup
    try:
        parsed_cleaned = clean_asyncpg_url(cleaned_url)
        return parsed_cleaned
    except Exception as e:
        logger.warning("URL parsing method failed, using string replacement result: %s", e)
        return cleaned_url

_db_url = robust_url_cleaning(_db_url)

# Multiple connection strategies for Supabase/Render connectivity issues
def get_connection_urls():
    """Get multiple database connection URLs to try in order"""
    base_url = _db_url
    urls = []
    
    # Strategy 1: Try connection pooling (port 6543) if currently using 5432
    if "supabase.co:5432" in base_url:
        pooled_url = base_url.replace(":5432", ":6543")
        urls.append(("Connection Pooling (6543)", pooled_url))
        logger.info("Added connection pooling URL strategy")
    
    # Strategy 2: Original URL with SSL enforcement
    if "sslmode=" not in base_url:
        ssl_url = base_url + ("&" if "?" in base_url else "?") + "sslmode=require"
        urls.append(("SSL Required", ssl_url))
    
    # Strategy 3: Original URL as-is
    urls.append(("Direct Connection", base_url))
    
    # Strategy 4: If using pooling, try direct connection
    if "supabase.co:6543" in base_url:
        direct_url = base_url.replace(":6543", ":5432")
        urls.append(("Direct (5432)", direct_url))
    
    return urls

# Try to create engine with different connection strategies
def create_database_engine():
    """Create database engine with fallback strategies"""
    urls_to_try = get_connection_urls()
    
    for strategy_name, url in urls_to_try:
        try:
            logger.info("Attempting database connection strategy: %s", strategy_name)
            engine = create_async_engine(
                url,
                pool_pre_ping=True,
                pool_size=3,  # Smaller pool for cloud environments
                max_overflow=5,
                pool_timeout=20,
                pool_recycle=1800,  # 30 minutes
                connect_args={
                    "command_timeout": 30,
                    "server_settings": {
                        "application_name": "nkt_easeme_api_render",
                        "search_path": "app,public",
                    },
                },
            )
            logger.info("Successfully created engine with strategy: %s", strategy_name)
            return engine
        except Exception as e:
            logger.warning("Strategy '%s' failed: %s", strategy_name, str(e))
            continue
    
    # If all strategies fail, create with the base URL and let it fail properly
    logger.error("All connection strategies failed, using base URL")
    return create_async_engine(_db_url, pool_pre_ping=True)

engine = create_database_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    """
    Dependency that provides a database session with retry logic.
    The search_path is now set at the connection level via server_settings.
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with SessionLocal() as session:
                yield session
                return
        except OSError as e:
            retry_count += 1
            if "Network is unreachable" in str(e) or "Connection refused" in str(e):
                logger.warning(
                    "Network connectivity issue (attempt %d/%d): %s", 
                    retry_count, max_retries, str(e)
                )
                if retry_count < max_retries:
                    import asyncio
                    await asyncio.sleep(1)  # Brief delay before retry
                    continue
            raise
        except Exception as e:
            logger.error("Database session error: %s", str(e))
            raise
