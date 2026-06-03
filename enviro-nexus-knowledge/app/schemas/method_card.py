from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


RequirementType = Literal[
    "sample_collection",
    "sample_preservation",
    "instrument",
    "interference",
    "analysis_step",
    "result_expression",
    "field_condition",
    "safety_note",
    "other",
]


class FactorIdentity(BaseModel):
    name: str
    aliases: list[str] = Field(min_length=1)


class MethodIdentity(BaseModel):
    category: str
    factor: str
    factors: list[FactorIdentity] = Field(min_length=1)
    aliases: list[str] = Field(min_length=1)
    standard_code: str
    standard_name: str
    method_name: str


class Applicability(BaseModel):
    scope_summary: str
    sample_types: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)


class MeasurementRange(BaseModel):
    lower: str | None = None
    upper: str | None = None
    unit: str | None = None


class Measurement(BaseModel):
    principle: str
    instrument: str
    unit: str | None = None
    range: MeasurementRange | None = None
    evidence_ids: list[str] = Field(min_length=1)


class Requirement(BaseModel):
    requirement_id: str
    type: RequirementType
    title: str
    content: str
    evidence_ids: list[str] = Field(min_length=1)


class QaQcItem(BaseModel):
    item_id: str
    title: str
    content: str
    evidence_ids: list[str] = Field(min_length=1)


class AnswerTemplate(BaseModel):
    short_answer: str
    evidence_ids: list[str] = Field(min_length=1)


class SourceDocumentRef(BaseModel):
    doc_id: str
    standard_code: str
    title: str


class EvidenceRef(BaseModel):
    evidence_id: str
    source_title: str
    section: str
    page: int | None = None
    summary: str


class Governance(BaseModel):
    review_status: Literal["draft", "reviewing", "approved", "rejected"]
    answer_visibility: Literal["enabled", "disabled"]


class ChangeLogItem(BaseModel):
    version: int
    date: str
    description: str


class MethodCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["method_card.v0.1"]
    card_id: str = Field(pattern=r"^[a-z0-9_]+$")
    card_version: int = Field(ge=1)
    identity: MethodIdentity
    applicability: Applicability
    measurement: Measurement
    requirements: list[Requirement] = Field(min_length=1)
    qa_qc: list[QaQcItem] = Field(min_length=1)
    answer_template: AnswerTemplate
    source_document: SourceDocumentRef
    evidence_refs: list[EvidenceRef] = Field(min_length=1)
    governance: Governance
    change_log: list[ChangeLogItem] = Field(min_length=1)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_method_card_links(self) -> "MethodCard":
        evidence_ids = [evidence.evidence_id for evidence in self.evidence_refs]
        evidence_id_set = set(evidence_ids)
        if len(evidence_ids) != len(evidence_id_set):
            raise ValueError("evidence_refs evidence_id must be unique")

        aliases = set(self.identity.aliases)
        factor_aliases = {
            alias
            for factor in self.identity.factors
            for alias in factor.aliases
        }
        missing_aliases = sorted(factor_aliases - aliases)
        if missing_aliases:
            raise ValueError(f"identity aliases must cover factor aliases: {missing_aliases}")

        missing_answer_template_ids = sorted(
            evidence_id
            for evidence_id in self.answer_template.evidence_ids
            if evidence_id not in evidence_id_set
        )
        if missing_answer_template_ids:
            raise ValueError(
                "answer_template evidence_ids reference missing evidence_refs: "
                f"{missing_answer_template_ids}"
            )

        missing_applicability_ids = sorted(
            evidence_id
            for evidence_id in self.applicability.evidence_ids
            if evidence_id not in evidence_id_set
        )
        if missing_applicability_ids:
            raise ValueError(
                "applicability evidence_ids reference missing evidence_refs: "
                f"{missing_applicability_ids}"
            )

        missing_measurement_ids = sorted(
            evidence_id
            for evidence_id in self.measurement.evidence_ids
            if evidence_id not in evidence_id_set
        )
        if missing_measurement_ids:
            raise ValueError(
                "measurement evidence_ids reference missing evidence_refs: "
                f"{missing_measurement_ids}"
            )

        missing_requirement_ids = sorted(
            evidence_id
            for requirement in self.requirements
            for evidence_id in requirement.evidence_ids
            if evidence_id not in evidence_id_set
        )
        if missing_requirement_ids:
            raise ValueError(
                "requirements evidence_ids reference missing evidence_refs: "
                f"{missing_requirement_ids}"
            )

        missing_qa_qc_ids = sorted(
            evidence_id
            for item in self.qa_qc
            for evidence_id in item.evidence_ids
            if evidence_id not in evidence_id_set
        )
        if missing_qa_qc_ids:
            raise ValueError(
                "qa_qc evidence_ids reference missing evidence_refs: "
                f"{missing_qa_qc_ids}"
            )

        return self
