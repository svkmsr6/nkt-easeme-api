from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Use the DATABASE_URL directly from environment with minimal cleanup
_db_url = str(settings.DATABASE_URL)

# Replace connect_timeout with command_timeout for asyncpg compatibility
if 'connect_timeout=' in _db_url:
    _db_url = _db_url.replace('connect_timeout=', 'command_timeout=')
    logger.info("Replaced connect_timeout with command_timeout in DATABASE_URL")

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
