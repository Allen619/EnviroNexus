import re

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


TITLE_SYSTEM_PROMPT = (
    "你是会话标题助手。根据用户的第一个问题生成一条简体中文标题，不超过20字，"
    "不要引号，不要句号，概括用户咨询主题。"
)


TITLE_MAX_LEN = 20
_TITLE_WRAPPER_CHARS = " \t\r\n\"'“”‘’《》「」『』:：-—"
_TITLE_TRAILING_PUNCT = "。.!！?？,，;；"
_THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_TAG_RE = re.compile(r"</?think\b[^>]*>", re.IGNORECASE)
_REASONING_PREFIXES = (
    "the user",
    "user ",
    "用户问的是",
    "用户询问",
    "用户想",
    "用户问",
    "助手",
)


def _is_displayable_title(text: str) -> bool:
    if not text:
        return False

    lowered = text.lower()
    if "<think" in lowered or "</think" in lowered:
        return False
    lowered = lowered.lstrip()
    return not any(lowered.startswith(prefix) for prefix in _REASONING_PREFIXES)


def clean_title_output(raw_title: object, first_user_message: str) -> str:
    original = raw_title if isinstance(raw_title, str) else str(raw_title)
    has_open_think = bool(re.search(r"<think\b", original, re.IGNORECASE))
    has_close_think = bool(re.search(r"</think>", original, re.IGNORECASE))

    if has_open_think and not has_close_think:
        return fallback_title(first_user_message)

    text = _THINK_BLOCK_RE.sub("", original).strip()
    lowered_text = text.lower()
    if _THINK_TAG_RE.search(text) or "<think" in lowered_text or "</think" in lowered_text:
        return fallback_title(first_user_message)

    text = re.sub(r"\s+", " ", text)
    text = text.strip(_TITLE_WRAPPER_CHARS)
    text = text.rstrip(_TITLE_TRAILING_PUNCT).strip(_TITLE_WRAPPER_CHARS)

    if not _is_displayable_title(text):
        return fallback_title(first_user_message)
    return text[:TITLE_MAX_LEN]


def build_title_input(user_msg: str, assistant_msg: str) -> str:
    return f"用户问题：{user_msg}"


def fallback_title(first_user_message: str) -> str:
    text = first_user_message.strip()
    if len(text) <= 30:
        return text
    return text[:29] + "…"
