import json
from pathlib import Path

from app.core.answer_builder import build_answer
from app.schemas.method_card import MethodCard


SEED_CARD_DIR = Path("data/seed/method_cards")


def test_build_answer_from_ph_method_card():
    payload = json.loads(Path("data/seed/method_cards/water_ph_hj1147_2020.json").read_text(encoding="utf-8"))
    card = MethodCard.model_validate(payload)

    answer = build_answer(card)

    assert answer["summary"] == "pH 值可采用 HJ 1147-2020《水质 pH 值的测定 电极法》测定。"
    assert answer["standard_code"] == "HJ 1147-2020"
    assert answer["standard_name"] == "水质 pH 值的测定 电极法"
    assert answer["method_name"] == "电极法"
    assert answer["applicability"]
    assert answer["measurement"]
    assert answer["requirements"]
    assert answer["qa_qc"]
    assert answer["evidence_refs"]
    assert "governance" not in answer
    assert "change_log" not in answer
    assert "source_document" not in answer
    assert "file_path" not in json.dumps(answer, ensure_ascii=False)


def test_build_answer_includes_evidence_for_answer_template_and_measurement_fields():
    payload = json.loads(Path("data/seed/method_cards/water_ph_hj1147_2020.json").read_text(encoding="utf-8"))
    card = MethodCard.model_validate(payload)

    answer = build_answer(card)
    evidence_sections = {evidence["section"] for evidence in answer["evidence_refs"]}

    assert "1 适用范围" in evidence_sections
    assert "3 方法原理" in evidence_sections
    assert "6 仪器和设备" in evidence_sections


def test_build_answer_from_every_seed_card_keeps_internal_metadata_out():
    for path in sorted(SEED_CARD_DIR.glob("*.json")):
        card = MethodCard.model_validate(json.loads(path.read_text(encoding="utf-8")))
        answer = build_answer(card)

        assert answer["summary"]
        assert answer["standard_code"] == card.identity.standard_code
        assert answer["standard_name"] == card.identity.standard_name
        assert answer["method_name"] == card.identity.method_name
        assert answer["applicability"]
        assert answer["measurement"]
        assert answer["requirements"]
        assert answer["qa_qc"]
        assert answer["evidence_refs"]
        serialized = json.dumps(answer, ensure_ascii=False)
        assert "governance" not in answer
        assert "change_log" not in answer
        assert "source_document" not in answer
        assert "file_path" not in serialized
        assert "evidence_ids" not in serialized
