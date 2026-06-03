from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ApiResponse


class FactorQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="用户问题（首尾空白会被 trim）")
    session_id: str = Field(..., min_length=1, description="会话 ID，须先 POST /api/v1/sessions 创建")

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("请输入问题内容")
        return stripped


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
