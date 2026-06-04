"""知识服务下游响应契约模型。"""

from pydantic import BaseModel, Field

from app.schemas.factor_query import EvidenceRefItem, FactorAnswer, RequirementItem


class KnowledgeRequirementItem(BaseModel):
    type: str = ""
    title: str = ""
    content: str = ""


class KnowledgeEvidenceRefItem(BaseModel):
    evidence_id: str | None = None
    source_title: str = ""
    section: str = ""
    summary: str = ""
    field_path: str | None = None


class KnowledgeFactorAnswer(BaseModel):
    summary: str = ""
    standard_code: str = ""
    standard_name: str = ""
    method_name: str = ""
    applicability: str = ""
    requirements: list[KnowledgeRequirementItem] = Field(default_factory=list)
    evidence_refs: list[KnowledgeEvidenceRefItem] = Field(default_factory=list)

    def to_factor_answer(self) -> FactorAnswer:
        return FactorAnswer(
            summary=self.summary,
            standard_code=self.standard_code,
            standard_name=self.standard_name,
            method_name=self.method_name,
            applicability=self.applicability,
            requirements=[
                RequirementItem(type=r.type, title=r.title, content=r.content)
                for r in self.requirements
            ],
            evidence_refs=[
                EvidenceRefItem(
                    source_title=e.source_title,
                    section=e.section,
                    summary=e.summary,
                )
                for e in self.evidence_refs
            ],
        )


class KnowledgeFactorQueryPayload(BaseModel):
    """知识服务因子查询响应体（顶层 JSON）。"""

    matched: bool = False
    factor: str | None = None
    matched_alias: str | None = None
    card_id: str | None = None
    answer: KnowledgeFactorAnswer | None = None
    warnings: list[str] = Field(default_factory=list)


class KnowledgeMethodCardIdentity(BaseModel):
    factor: str | None = None


class KnowledgeMethodCardContent(BaseModel):
    card_id: str | None = None
    identity: KnowledgeMethodCardIdentity | None = None


class KnowledgeMethodCardPayload(BaseModel):
    """知识服务方法卡详情响应体。"""

    card: KnowledgeMethodCardContent | None = None
