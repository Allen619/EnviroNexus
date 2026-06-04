from app.core.api_message import (
    KNOWLEDGE_QUERY_NOT_MATCHED_REPLY,
    QUERY_REWRITE_SYSTEM_PROMPT,
)


def test_query_rewrite_prompt_is_defined_in_api_message():
    assert "EnviroNexus 知识库查询改写器" in QUERY_REWRITE_SYSTEM_PROMPT
    assert "只输出合法 JSON" in QUERY_REWRITE_SYSTEM_PROMPT
    assert "COD 和 CODMn 必须严格区分" in QUERY_REWRITE_SYSTEM_PROMPT


def test_knowledge_not_matched_reply_is_defined_in_api_message():
    assert KNOWLEDGE_QUERY_NOT_MATCHED_REPLY == "与知识库不匹配，请重试"
