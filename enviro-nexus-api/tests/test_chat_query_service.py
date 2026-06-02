from unittest.mock import AsyncMock

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.schemas.knowledge import (
    KnowledgeEvidenceRefItem,
    KnowledgeFactorAnswer,
    KnowledgeFactorQueryPayload,
)
from app.services.chat_query_service import ChatQueryService
from app.services.session_store import InMemorySessionStore


@pytest.mark.asyncio
async def test_query_returns_reply_and_sources():
    store = InMemorySessionStore(ttl_seconds=3600)
    llm = FakeListChatModel(responses=["COD 可用 HJ 828-2017 测定。"])
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = KnowledgeFactorQueryPayload(
        matched=True,
        factor="化学需氧量",
        card_id="water_cod_hj828_2017",
        answer=KnowledgeFactorAnswer(
            standard_code="HJ 828-2017",
            evidence_refs=[
                KnowledgeEvidenceRefItem(
                    evidence_id="ev_001",
                    source_title="HJ 828-2017",
                    section="适用范围",
                    summary="适用范围说明",
                    field_path="applicability.scope_summary",
                )
            ],
        ),
    )
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=llm,
        summarizer=FakeListChatModel(responses=["摘要"]),
        max_recent_messages=6,
        char_threshold=100000,
    )
    resp = await svc.query(query="COD怎么测", request_id="req-1", session_id=None)
    assert resp.data.session_id
    assert resp.data.matched is True
    assert "HJ" in resp.data.reply
    assert len(resp.data.sources) == 1
    assert resp.data.sources[0].source_title == "HJ 828-2017"


@pytest.mark.asyncio
async def test_not_matched_appends_session():
    store = InMemorySessionStore(ttl_seconds=3600)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = KnowledgeFactorQueryPayload(matched=False)
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["不应调用"]),
        summarizer=FakeListChatModel(responses=["摘要"]),
        char_threshold=100000,
    )
    resp = await svc.query(query="未知因子", request_id=None, session_id=None)
    assert resp.code == "FACTOR_NOT_FOUND"
    assert resp.data.sources == []
    loaded = await store.get(resp.data.session_id)
    assert loaded is not None
    assert len(loaded.messages) == 2
