from typing import Any

from pydantic import BaseModel


class FactorQueryResponse(BaseModel):
    api_version: str
    matched: bool
    factor: str | None
    matched_alias: str | None
    match_confidence: float
    card_id: str | None
    answer: dict[str, Any] | None
    warnings: list[str]


class PublicMeasurementRange(BaseModel):
    lower: str | None = None
    upper: str | None = None
    unit: str | None = None


class PublicMeasurement(BaseModel):
    principle: str
    instrument: str
    unit: str | None = None
    range: PublicMeasurementRange | None = None


class PublicRequirement(BaseModel):
    type: str
    title: str
    content: str


class PublicQaQcItem(BaseModel):
    title: str
    content: str


class PublicEvidenceRef(BaseModel):
    source_title: str
    section: str
    page: int | None = None
    summary: str


class PublicMethodCardSummary(BaseModel):
    card_id: str
    factor: str
    category: str
    standard_code: str
    standard_name: str
    method_name: str
    applicability: str


class PublicMethodCardDetail(PublicMethodCardSummary):
    measurement: PublicMeasurement
    requirements: list[PublicRequirement]
    qa_qc: list[PublicQaQcItem]
    evidence_refs: list[PublicEvidenceRef]


class PublicMethodCardListResponse(BaseModel):
    api_version: str
    items: list[PublicMethodCardSummary]
    count: int


class PublicMethodCardDetailResponse(BaseModel):
    api_version: str
    card: PublicMethodCardDetail


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    api_version: str
