from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.routes import health, tasks, interventions, checkins, dashboard, ai
from app.schemas.common import ErrorResponse, DatabaseError
import logging

def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.APP_NAME)
    logger = logging.getLogger(__name__)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )
    
    # Exception handlers
    @app.exception_handler(ProgrammingError)
    async def programming_error_handler(request: Request, exc: ProgrammingError):
        logger.error(f"Database programming error: {exc}")
        # Check if it's a column not found error
        if "does not exist" in str(exc):
            return JSONResponse(
                status_code=503,  # Service Unavailable
                content={
                    "error": "Database schema mismatch detected",
                    "detail": "The application schema is out of sync with the database. Please contact support.",
                    "error_code": "SCHEMA_MISMATCH"
                }
            )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database query error",
                "detail": "There was an error executing the database query",
                "error_code": "DATABASE_ERROR"
            }
        )
    
    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError):
        logger.error(f"Database operational error: {exc}")
        return JSONResponse(
            status_code=503,
            content={
                "error": "Database connection error",
                "detail": "Unable to connect to the database. Please try again later.",
                "error_code": "DATABASE_CONNECTION_ERROR"
            }
        )
    
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.error(f"Database integrity error: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Data integrity violation",
                "detail": "The operation violates database constraints",
                "error_code": "DATA_INTEGRITY_ERROR"
            }
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
