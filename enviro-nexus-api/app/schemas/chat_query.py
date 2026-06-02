from pydantic import BaseModel, Field

from app.schemas.common import ApiResponse


class FactorQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    session_id: str | None = None


class SourceItem(BaseModel):
    evidence_id: str | None = None
    source_title: str = ""
    section: str = ""
    summary: str = ""
    field_path: str | None = None


class FactorQueryData(BaseModel):
    session_id: str
    matched: bool
    reply: str
    factor: str | None = None
    matched_alias: str | None = None
    card_id: str | None = None
    sources: list[SourceItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


FactorQueryResponse = ApiResponse[FactorQueryData]
