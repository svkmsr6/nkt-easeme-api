from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# `settings.DATABASE_URL` is a Pydantic AnyUrl. SQLAlchemy expects a string or URL object.
# Convert to string to avoid: ArgumentError: Expected string or URL object, got AnyUrl(...)
_db_url = str(settings.DATABASE_URL)
# Ensure an async DB driver is specified for SQLAlchemy asyncio. If the URL is
# a plain `postgresql://...` convert it to `postgresql+asyncpg://...` so the
# asyncpg driver is used. This avoids InvalidRequestError when a sync driver
# (psycopg2) is present in the environment.
if _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_db_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with SessionLocal() as session:
        yield session
