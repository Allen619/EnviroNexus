from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine
from app.settings import get_settings


router = APIRouter()


@router.get("/health", response_model=None)
def health_check() -> dict[str, str] | JSONResponse:
    settings = get_settings()

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "enviro-nexus-knowledge",
                "api_version": settings.api_version,
                "database": "unavailable",
            },
        )

    return {
        "status": "ok",
        "service": "enviro-nexus-knowledge",
        "api_version": settings.api_version,
        "database": "ok",
    }
