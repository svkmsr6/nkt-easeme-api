import asyncio
import logging
from app.db.session import engine
from app.db.models import Base

logger = logging.getLogger(__name__)

async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise

async def init_models():
    await init_db()

if __name__ == "__main__":
    asyncio.run(init_models())
