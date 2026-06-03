from app.schemas.method_card import MethodCard


def build_public_method_card_summary(card: MethodCard) -> dict:
    return {
        "card_id": card.card_id,
        "factor": card.identity.factor,
        "category": card.identity.category,
        "standard_code": card.identity.standard_code,
        "standard_name": card.identity.standard_name,
        "method_name": card.identity.method_name,
        "applicability": card.applicability.scope_summary,
    }


def build_public_method_card_detail(card: MethodCard) -> dict:
    measurement_range = card.measurement.range
    return {
        **build_public_method_card_summary(card),
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
        "evidence_refs": [
            {
                "source_title": evidence.source_title,
                "section": evidence.section,
                "page": evidence.page,
                "summary": evidence.summary,
            }
            for evidence in card.evidence_refs
        ],
    }
