from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import logging

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

# Create engine with better connection pool settings and timeouts
engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Maximum number of connections to keep in the pool
    max_overflow=10,  # Maximum overflow connections beyond pool_size
    pool_timeout=30,  # Timeout for getting a connection from the pool (seconds)
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "timeout": 10,  # Connection timeout in seconds
        "command_timeout": 60,  # Command execution timeout in seconds
        "server_settings": {
            "application_name": "nkt_easeme_api",
            "search_path": "app,public",  # Set search_path at connection level
        },
    },
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    """
    Dependency that provides a database session.
    The search_path is now set at the connection level via server_settings,
    so we don't need to execute it on every request.
    """
    try:
        async with SessionLocal() as session:
            yield session
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        raise
