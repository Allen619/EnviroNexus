import json
from pathlib import Path

from app.core.public_method_card_builder import (
    build_public_method_card_detail,
    build_public_method_card_summary,
)
from app.schemas.method_card import MethodCard


BLOCKED_PUBLIC_FIELDS = [
    "governance",
    "review_status",
    "answer_visibility",
    "change_log",
    "extensions",
    "source_document",
    "source_doc_id",
    "file_path",
    "metadata",
    "checksum_sha256",
    "manual_extract_source",
    "needs_pdf_check",
    "evidence_id",
    "evidence_ids",
]


def load_card(card_id: str) -> MethodCard:
    path = Path("data/seed/method_cards") / f"{card_id}.json"
    return MethodCard.model_validate(json.loads(path.read_text(encoding="utf-8")))


def assert_no_internal_fields(payload: dict) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    for field_name in BLOCKED_PUBLIC_FIELDS:
        assert field_name not in serialized


def test_build_public_method_card_summary_omits_governance_and_internal_fields():
    card = load_card("water_ph_hj1147_2020")

    summary = build_public_method_card_summary(card)

    assert summary == {
        "card_id": "water_ph_hj1147_2020",
        "factor": "pH 值",
        "category": "水质",
        "standard_code": "HJ 1147-2020",
        "standard_name": "水质 pH 值的测定 电极法",
        "method_name": "电极法",
        "applicability": card.applicability.scope_summary,
    }
    assert_no_internal_fields(summary)


def test_build_public_method_card_detail_returns_frontend_safe_fields():
    card = load_card("water_ph_hj1147_2020")

    detail = build_public_method_card_detail(card)

    assert detail["card_id"] == "water_ph_hj1147_2020"
    assert detail["factor"] == "pH 值"
    assert detail["category"] == "水质"
    assert detail["standard_code"] == "HJ 1147-2020"
    assert detail["standard_name"] == "水质 pH 值的测定 电极法"
    assert detail["method_name"] == "电极法"
    assert detail["applicability"] == card.applicability.scope_summary
    assert detail["measurement"] == {
        "principle": card.measurement.principle,
        "instrument": card.measurement.instrument,
        "unit": card.measurement.unit,
        "range": {
            "lower": "0",
            "upper": "14",
            "unit": "pH",
        },
    }
    assert detail["requirements"]
    assert detail["qa_qc"]
    assert detail["evidence_refs"]
    assert set(detail["evidence_refs"][0].keys()) == {
        "source_title",
        "section",
        "page",
        "summary",
    }
    assert_no_internal_fields(detail)
