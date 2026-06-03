from app.schemas.method_card import EvidenceRef, MethodCard


def collect_answer_evidence_refs(card: MethodCard) -> list[dict]:
    selected_ids: set[str] = set(card.answer_template.evidence_ids)
    selected_ids.update(card.applicability.evidence_ids)
    selected_ids.update(card.measurement.evidence_ids)
    for requirement in card.requirements:
        selected_ids.update(requirement.evidence_ids)
    for qa_qc_item in card.qa_qc:
        selected_ids.update(qa_qc_item.evidence_ids)

    return [
        _serialize_evidence_ref(evidence)
        for evidence in card.evidence_refs
        if evidence.evidence_id in selected_ids
    ]


def _serialize_evidence_ref(evidence: EvidenceRef) -> dict:
    return {
        "source_title": evidence.source_title,
        "section": evidence.section,
        "page": evidence.page,
        "summary": evidence.summary,
    }
