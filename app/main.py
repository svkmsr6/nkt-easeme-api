from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.routes import health, tasks, interventions, checkins, dashboard, ai

def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.APP_NAME)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )
    # routes
    app.include_router(health.router)
    app.include_router(tasks.router)
    app.include_router(interventions.router)
    app.include_router(checkins.router)
    app.include_router(dashboard.router)
    app.include_router(ai.router)
    return app

app = create_app()
