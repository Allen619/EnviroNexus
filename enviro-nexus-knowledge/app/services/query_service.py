from sqlalchemy.orm import Session

from app.core.answer_builder import build_answer
from app.core.factor_matcher import choose_best_match
from app.core.normalizer import normalize_query
from app.db.repositories import get_enabled_method_card_json, list_alias_candidates
from app.schemas.method_card import MethodCard
from app.settings import get_settings


UNMATCHED_WARNING = "当前知识库暂未收录该检测因子，请人工确认后再使用。"


class EmptyQueryError(ValueError):
    error_code = "empty_query"


def query_factor(query: str, session: Session) -> dict:
    if not query.strip():
        raise EmptyQueryError("query must not be empty")

    settings = get_settings()
    normalized_query = normalize_query(query)
    match = choose_best_match(normalized_query, list_alias_candidates(session))
    if match is None:
        return _unmatched_response(settings.api_version)

    card_json = get_enabled_method_card_json(session, match.card_id)
    if card_json is None:
        return _unmatched_response(settings.api_version)

    card = MethodCard.model_validate(card_json)
    return {
        "api_version": settings.api_version,
        "matched": True,
        "factor": match.factor,
        "matched_alias": match.alias,
        "match_confidence": match.confidence,
        "card_id": match.card_id,
        "answer": build_answer(card),
        "warnings": [],
    }


def _unmatched_response(api_version: str) -> dict:
    return {
        "api_version": api_version,
        "matched": False,
        "factor": None,
        "matched_alias": None,
        "match_confidence": 0.0,
        "card_id": None,
        "answer": None,
        "warnings": [UNMATCHED_WARNING],
    }
