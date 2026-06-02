from app.schemas.knowledge import KnowledgeFactorQueryPayload

REPLY_SYSTEM_PROMPT = """你是环检智枢的环保检测标准方法助手。
仅根据【本轮知识库检索】与【会话摘要】中的事实用简体中文回答。
若 matched 为 false，说明知识库未收录，不要编造标准号或方法细节。
正文不要伪造引用编号；依据由接口 sources 字段提供。"""

NOT_MATCHED_REPLY_FALLBACK = "当前知识库暂未收录该检测因子，请人工确认后再使用。"


def build_knowledge_block(payload: KnowledgeFactorQueryPayload) -> str:
    if not payload.matched:
        return "【本轮知识库检索】\nmatched: false"

    lines = [
        "【本轮知识库检索】",
        "matched: true",
        f"factor: {payload.factor}",
        f"card_id: {payload.card_id}",
    ]
    ans = payload.answer
    if ans:
        lines.extend(
            [
                f"standard_code: {ans.standard_code}",
                f"standard_name: {ans.standard_name}",
                f"method_name: {ans.method_name}",
                f"applicability: {ans.applicability}",
                f"summary: {ans.summary}",
            ]
        )
        for req in ans.requirements:
            lines.append(f"要求[{req.type}] {req.title}: {req.content}")
        for evidence in ans.evidence_refs:
            lines.append(
                f"依据: {evidence.source_title} / {evidence.section} / "
                f"{evidence.summary} / {evidence.field_path}"
            )
    return "\n".join(lines)
