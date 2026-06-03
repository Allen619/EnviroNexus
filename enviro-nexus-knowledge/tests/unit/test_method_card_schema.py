import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.method_card import MethodCard


SEED_CARD_PATH = Path("data/seed/method_cards/water_ph_hj1147_2020.json")
SEED_CARD_DIR = Path("data/seed/method_cards")
SAMPLE_QUERIES_PATH = Path("data/seed/sample_queries.json")
EXPECTED_CARD_IDS = {
    "gas_smoke_blackness_hj1287_2023",
    "gas_thc_methane_nmhc_hj1332_2023",
    "water_colority_hj1182_2021",
    "water_permanganate_index_hj1445_2026",
    "water_ph_hj1147_2020",
}
EXPECTED_SAMPLE_QUERIES = {
    "pH 怎么测？": ("water_ph_hj1147_2020", True),
    "水样酸碱度用什么标准？": ("water_ph_hj1147_2020", True),
    "PH值检测方法": ("water_ph_hj1147_2020", True),
    "色度怎么测？": ("water_colority_hj1182_2021", True),
    "CODMn 怎么测？": ("water_permanganate_index_hj1445_2026", True),
    "烟气黑度怎么测？": ("gas_smoke_blackness_hj1287_2023", True),
    "非甲烷总烃怎么测？": ("gas_thc_methane_nmhc_hj1332_2023", True),
    "COD 怎么测？": (None, False),
}


def load_seed_card() -> dict:
    return json.loads(SEED_CARD_PATH.read_text(encoding="utf-8"))


def load_all_seed_cards() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SEED_CARD_DIR.glob("*.json"))
    ]


def test_all_method_card_seeds_pass_schema_validation():
    cards = [MethodCard.model_validate(payload) for payload in load_all_seed_cards()]
    card_ids = {card.card_id for card in cards}

    assert card_ids == EXPECTED_CARD_IDS
    for card in cards:
        assert card.schema_version == "method_card.v0.1"
        assert card.answer_template.evidence_ids
        assert card.applicability.evidence_ids
        assert card.measurement.evidence_ids


def test_ph_method_card_seed_passes_schema_validation():
    card = MethodCard.model_validate(load_seed_card())

    assert card.schema_version == "method_card.v0.1"
    assert card.card_id == "water_ph_hj1147_2020"
    assert card.identity.factor == "pH 值"


def test_sample_queries_expected_card_ids_match_day1_5_cards():
    queries = json.loads(SAMPLE_QUERIES_PATH.read_text(encoding="utf-8"))

    actual = {
        item["query"]: (item["expected_card_id"], item["expected_matched"])
        for item in queries
    }

    assert actual == EXPECTED_SAMPLE_QUERIES


def test_requirements_type_rejects_sample():
    payload = deepcopy(load_seed_card())
    payload["requirements"][0]["type"] = "sample"

    with pytest.raises(ValidationError):
        MethodCard.model_validate(payload)


def test_requirement_evidence_ids_must_exist():
    payload = deepcopy(load_seed_card())
    payload["requirements"][0]["evidence_ids"] = ["missing_evidence"]

    with pytest.raises(ValidationError, match="requirements evidence_ids"):
        MethodCard.model_validate(payload)


def test_qa_qc_evidence_ids_must_exist():
    payload = deepcopy(load_seed_card())
    payload["qa_qc"][0]["evidence_ids"] = ["missing_evidence"]

    with pytest.raises(ValidationError, match="qa_qc evidence_ids"):
        MethodCard.model_validate(payload)


def test_answer_template_evidence_ids_must_exist():
    payload = deepcopy(load_seed_card())
    payload["answer_template"]["evidence_ids"] = ["missing_evidence"]

    with pytest.raises(ValidationError, match="answer_template evidence_ids"):
        MethodCard.model_validate(payload)


def test_applicability_evidence_ids_must_be_non_empty():
    payload = deepcopy(load_seed_card())
    payload["applicability"]["evidence_ids"] = []

    with pytest.raises(ValidationError):
        MethodCard.model_validate(payload)


def test_measurement_evidence_ids_must_exist():
    payload = deepcopy(load_seed_card())
    payload["measurement"]["evidence_ids"] = ["missing_evidence"]

    with pytest.raises(ValidationError, match="measurement evidence_ids"):
        MethodCard.model_validate(payload)


def test_identity_aliases_must_cover_factor_aliases():
    payload = deepcopy(load_seed_card())
    payload["identity"]["aliases"] = ["pH", "PH", "pH值", "PH值"]

    with pytest.raises(ValidationError, match="identity aliases"):
        MethodCard.model_validate(payload)
