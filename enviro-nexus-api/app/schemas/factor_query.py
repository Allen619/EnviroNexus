from pydantic import BaseModel

from app.schemas.common import ApiResponse


class RequirementItem(BaseModel):
    type: str
    title: str
    content: str


class EvidenceRefItem(BaseModel):
    source_title: str
    section: str
    summary: str


class FactorAnswer(BaseModel):
    summary: str
    standard_code: str
    standard_name: str
    method_name: str
    applicability: str
    requirements: list[RequirementItem] = []
    evidence_refs: list[EvidenceRefItem] = []


class MethodCardIdentity(BaseModel):
    factor: str | None = None


class MethodCardContent(BaseModel):
    card_id: str | None = None
    identity: MethodCardIdentity | None = None


class MethodCardData(BaseModel):
    card: MethodCardContent | None = None


MethodCardResponse = ApiResponse[MethodCardData]
