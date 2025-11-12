from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.routes import health, tasks, interventions, checkins, dashboard, ai
from app.db.init_db import init_db

async def startup():
    """Initialize database on startup"""
    await init_db()

def create_app() -> FastAPI:
    configure_logging()
    fastapi_app = FastAPI(title=settings.APP_NAME)
    fastapi_app.add_event_handler("startup", startup)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )
    # routes
    fastapi_app.include_router(health.router)
    fastapi_app.include_router(tasks.router)
    fastapi_app.include_router(interventions.router)
    fastapi_app.include_router(checkins.router)
    fastapi_app.include_router(dashboard.router)
    fastapi_app.include_router(ai.router)
    return fastapi_app

app = create_app()
