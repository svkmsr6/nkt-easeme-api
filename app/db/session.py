from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)

# Use the DATABASE_URL directly from environment with proper parameter handling
_db_url = str(settings.DATABASE_URL)

# Handle asyncpg parameter compatibility with simple string replacement
# Just replace connect_timeout with command_timeout and remove problematic parameters
if 'connect_timeout=' in _db_url:
    _db_url = re.sub(r'connect_timeout=', 'command_timeout=', _db_url)
    logger.info("Replaced connect_timeout with command_timeout in DATABASE_URL")

# Remove problematic parameters that asyncpg doesn't support
problematic_params = ['server_settings', 'passfile', 'channel_binding', 'gssencmode']
for param in problematic_params:
    if f'{param}=' in _db_url:
        # Remove the parameter and its value (handles both &param=value and ?param=value)
        _db_url = re.sub(rf'[&?]{param}=[^&]*', '', _db_url)
        logger.info(f"Removed unsupported parameter: {param}")

# Clean up any double & or trailing &
_db_url = re.sub(r'&+', '&', _db_url)
_db_url = re.sub(r'[?&]$', '', _db_url)

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
