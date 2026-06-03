from app.core.evidence_builder import collect_answer_evidence_refs
from app.schemas.method_card import MethodCard


def build_answer(card: MethodCard) -> dict:
    measurement_range = card.measurement.range
    return {
        "summary": card.answer_template.short_answer,
        "standard_code": card.identity.standard_code,
        "standard_name": card.identity.standard_name,
        "method_name": card.identity.method_name,
        "applicability": card.applicability.scope_summary,
        "measurement": {
            "principle": card.measurement.principle,
            "instrument": card.measurement.instrument,
            "unit": card.measurement.unit,
            "range": None
            if measurement_range is None
            else {
                "lower": measurement_range.lower,
                "upper": measurement_range.upper,
                "unit": measurement_range.unit,
            },
        },
        "requirements": [
            {
                "type": requirement.type,
                "title": requirement.title,
                "content": requirement.content,
            }
            for requirement in card.requirements
        ],
        "qa_qc": [
            {
                "title": item.title,
                "content": item.content,
            }
            for item in card.qa_qc
        ],
        "evidence_refs": collect_answer_evidence_refs(card),
    }
