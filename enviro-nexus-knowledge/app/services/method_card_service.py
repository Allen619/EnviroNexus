from sqlalchemy.orm import Session

from app.core.public_method_card_builder import (
    build_public_method_card_detail,
    build_public_method_card_summary,
)
from app.db.repositories import get_public_method_card_json, list_public_method_card_jsons
from app.schemas.method_card import MethodCard
from app.settings import get_settings


class MethodCardNotFoundError(ValueError):
    error_code = "method_card_not_found"


def list_public_method_cards(session: Session) -> dict:
    settings = get_settings()
    cards = [
        MethodCard.model_validate(payload)
        for payload in list_public_method_card_jsons(session)
    ]
    items = [build_public_method_card_summary(card) for card in cards]
    return {
        "api_version": settings.api_version,
        "items": items,
        "count": len(items),
    }


def get_public_method_card(card_id: str, session: Session) -> dict:
    settings = get_settings()
    payload = get_public_method_card_json(session, card_id)
    if payload is None:
        raise MethodCardNotFoundError("method card is not found or not public")

    card = MethodCard.model_validate(payload)
    return {
        "api_version": settings.api_version,
        "card": build_public_method_card_detail(card),
    }
