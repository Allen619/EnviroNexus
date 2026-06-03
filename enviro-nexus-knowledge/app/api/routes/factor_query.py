from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.schemas.query import FactorQueryRequest
from app.services.query_service import EmptyQueryError, query_factor
from app.settings import get_settings


router = APIRouter()


@router.post("/factors/query", response_model=None)
def factor_query(request: FactorQueryRequest) -> dict | JSONResponse:
    settings = get_settings()

    try:
        with SessionLocal() as session:
            return query_factor(request.query, session)
    except EmptyQueryError:
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "empty_query",
                "message": "query must not be empty",
                "api_version": settings.api_version,
            },
        )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "database_unavailable",
                "message": "database is unavailable",
                "api_version": settings.api_version,
            },
        )
