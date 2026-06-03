from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.schemas.response import PublicMethodCardDetailResponse, PublicMethodCardListResponse
from app.services.method_card_service import (
    MethodCardNotFoundError,
    get_public_method_card,
    list_public_method_cards,
)
from app.settings import get_settings


router = APIRouter()


@router.get("/method-cards", response_model=PublicMethodCardListResponse)
def list_method_cards() -> dict | JSONResponse:
    settings = get_settings()
    try:
        with SessionLocal() as session:
            return list_public_method_cards(session)
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "database_unavailable",
                "message": "database is unavailable",
                "api_version": settings.api_version,
            },
        )


@router.get("/method-cards/{card_id}/public", response_model=PublicMethodCardDetailResponse)
def get_method_card_public(card_id: str) -> dict | JSONResponse:
    settings = get_settings()
    try:
        with SessionLocal() as session:
            return get_public_method_card(card_id, session)
    except MethodCardNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error_code": "method_card_not_found",
                "message": "method card is not found or not public",
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
