import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.core.api_message import KNOWLEDGE_QUERY_NOT_MATCHED_REPLY
from app.core.exceptions import SessionNotFoundError
from app.llm.prompts import fallback_title
from app.schemas.knowledge import (
    KnowledgeEvidenceRefItem,
    KnowledgeFactorAnswer,
    KnowledgeFactorQueryPayload,
)
from app.schemas.session import SessionRecord
from app.services.chat_query_service import ChatQueryService
from app.services.session_store import InMemorySessionStore


async def _create_session(store: InMemorySessionStore, user_id: str) -> str:
    import uuid

    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await store.create(
        SessionRecord(session_id=sid, user_id=user_id, created_at=now, updated_at=now)
    )
    return sid


def _matched_payload() -> KnowledgeFactorQueryPayload:
    return KnowledgeFactorQueryPayload(
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


def _rewrite_response(
    *,
    should_query_knowledge: bool = True,
    known_supported_factor: bool = True,
    rewritten_query: str = "高锰酸盐指数 怎么测？",
    factor_name: str | None = "高锰酸盐指数",
    confidence: float = 0.95,
) -> str:
    return json.dumps(
        {
            "should_query_knowledge": should_query_knowledge,
            "known_supported_factor": known_supported_factor,
            "rewritten_query": rewritten_query,
            "factor_name": factor_name,
            "confidence": confidence,
        },
        ensure_ascii=False,
    )


class BrokenSummarizer(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "broken"

    async def _agenerate(self, *args, **kwargs):
        raise RuntimeError("summarizer down")

    def _generate(self, *args, **kwargs):
        raise RuntimeError("summarizer down")


@pytest.mark.asyncio
async def test_query_returns_reply_and_sources():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    llm = FakeListChatModel(responses=["COD 可用 HJ 828-2017 测定。"])
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=llm,
        summarizer=FakeListChatModel(responses=["摘要"]),
        max_recent_messages=6,
        char_threshold=100000,
    )
    resp = await svc.query(
        query="COD怎么测",
        factor_name="化学需氧量",
        request_id="req-1",
        session_id=session_id,
        user_id=user_id,
    )
    assert resp.data.session_id == session_id
    assert resp.data.matched is True
    assert "HJ" in resp.data.reply
    assert len(resp.data.sources) == 1
    assert resp.data.sources[0].source_title == "HJ 828-2017"
    assert resp.data.warnings == []
    knowledge.query_factor.assert_awaited_once_with("COD怎么测")


@pytest.mark.asyncio
async def test_query_rewrites_user_query_before_knowledge_lookup():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["高锰酸盐指数可按标准方法测定。"]),
        summarizer=FakeListChatModel(responses=["标题"]),
        rewrite_model=FakeListChatModel(
            responses=[
                _rewrite_response(
                    rewritten_query="高锰酸盐指数 怎么测？",
                    factor_name="高锰酸盐指数",
                )
            ]
        ),
        char_threshold=100000,
    )

    await svc.query(
        query="耗氧量检测方法是什么？",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )

    knowledge.query_factor.assert_awaited_once_with("高锰酸盐指数 怎么测？")


@pytest.mark.asyncio
async def test_query_rewrite_accepts_json_with_model_reasoning_prefix():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    raw_rewrite = (
        "Let me construct the JSON response.\n"
        "</think>\n"
        '{"should_query_knowledge":true,"known_supported_factor":true,'
        '"rewritten_query":"色度 怎么测？","factor_name":"色度","confidence":0.98}'
    )
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["色度可按标准方法测定。"]),
        summarizer=FakeListChatModel(responses=["标题"]),
        rewrite_model=FakeListChatModel(responses=[raw_rewrite]),
        char_threshold=100000,
    )

    await svc.query(
        query="色度怎么测？",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )

    knowledge.query_factor.assert_awaited_once_with("色度 怎么测？")


@pytest.mark.asyncio
async def test_query_calls_knowledge_when_rewriter_has_no_factor_name():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = KnowledgeFactorQueryPayload(matched=False)
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["不应调用"]),
        summarizer=FakeListChatModel(responses=["标题"]),
        rewrite_model=FakeListChatModel(
            responses=[
                _rewrite_response(
                    should_query_knowledge=True,
                    known_supported_factor=False,
                    rewritten_query="COD 怎么测？",
                    factor_name=None,
                    confidence=0.8,
                )
            ]
        ),
        char_threshold=100000,
    )

    resp = await svc.query(
        query="COD 怎么测？",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )

    assert resp.code == "FACTOR_NOT_FOUND"
    knowledge.query_factor.assert_awaited_once_with("COD 怎么测？")


@pytest.mark.asyncio
async def test_query_returns_not_matched_reply_when_rewriter_cannot_infer_factor():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["不应调用"]),
        summarizer=FakeListChatModel(responses=["标题"]),
        rewrite_model=FakeListChatModel(
            responses=[
                _rewrite_response(
                    should_query_knowledge=False,
                    known_supported_factor=False,
                    rewritten_query="",
                    factor_name=None,
                    confidence=0.1,
                )
            ]
        ),
        char_threshold=100000,
    )

    resp = await svc.query(
        query="今天适合吃什么？",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )

    assert resp.code == "FACTOR_NOT_FOUND"
    assert resp.data.reply == KNOWLEDGE_QUERY_NOT_MATCHED_REPLY
    assert resp.data.factor is None
    assert resp.data.sources == []
    knowledge.query_factor.assert_not_called()


@pytest.mark.asyncio
async def test_not_matched_appends_session_with_empty_sources():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = KnowledgeFactorQueryPayload(matched=False)
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["不应调用"]),
        summarizer=FakeListChatModel(responses=["摘要"]),
        char_threshold=100000,
    )
    resp = await svc.query(
        query="未知因子",
        factor_name="未知因子",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )
    assert resp.code == "FACTOR_NOT_FOUND"
    assert resp.data.sources == []
    loaded = await store.get(session_id)
    assert loaded is not None
    assert len(loaded.messages) == 2
    assert loaded.messages[1].sources == []


@pytest.mark.asyncio
async def test_query_requires_existing_session():
    store = InMemorySessionStore()
    svc = ChatQueryService(
        knowledge_client=AsyncMock(),
        session_store=store,
        chat_model=FakeListChatModel(responses=["x"]),
        summarizer=FakeListChatModel(responses=["y"]),
        char_threshold=100000,
    )
    with pytest.raises(SessionNotFoundError):
        await svc.query(
            query="COD",
            factor_name="化学需氧量",
            request_id=None,
            session_id="nonexistent",
            user_id="user-1",
        )


@pytest.mark.asyncio
async def test_query_wrong_user():
    store = InMemorySessionStore()
    owner = "owner"
    session_id = await _create_session(store, owner)
    svc = ChatQueryService(
        knowledge_client=AsyncMock(),
        session_store=store,
        chat_model=FakeListChatModel(responses=["x"]),
        summarizer=FakeListChatModel(responses=["y"]),
        char_threshold=100000,
    )
    with pytest.raises(SessionNotFoundError):
        await svc.query(
            query="COD",
            factor_name="化学需氧量",
            request_id=None,
            session_id=session_id,
            user_id="other-user",
        )


@pytest.mark.asyncio
async def test_query_persists_sources_on_assistant_message():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["reply text"]),
        summarizer=FakeListChatModel(responses=["标题"]),
        char_threshold=100000,
    )
    await svc.query(
        query="COD怎么测",
        factor_name="化学需氧量",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )
    loaded = await store.get(session_id)
    assert loaded is not None
    assert len(loaded.messages) == 2
    assert len(loaded.messages[1].sources) == 1
    assert loaded.messages[1].sources[0].evidence_id == "ev_001"


@pytest.mark.asyncio
async def test_query_generates_title_after_first_turn():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    chat_model = FakeListChatModel(responses=["采用 HJ 828-2017 测定。"])
    summarizer = FakeListChatModel(responses=["COD测定咨询"])
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=chat_model,
        summarizer=summarizer,
        char_threshold=100000,
    )
    await svc.query(
        query="COD怎么测",
        factor_name="化学需氧量",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )
    loaded = await store.get(session_id)
    assert loaded is not None
    assert loaded.title == "COD测定咨询"


@pytest.mark.asyncio
async def test_query_persists_cleaned_title_after_first_turn():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["采用 HJ 828-2017 测定。"]),
        summarizer=FakeListChatModel(
            responses=["<think>分析首轮问答</think>COD测定咨询"]
        ),
        char_threshold=100000,
    )

    await svc.query(
        query="COD怎么测",
        factor_name="化学需氧量",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )

    loaded = await store.get(session_id)
    assert loaded is not None
    assert loaded.title == "COD测定咨询"


@pytest.mark.asyncio
async def test_query_title_fallback_when_generated_title_is_reasoning_residue():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    query_text = "COD怎么测"
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["采用 HJ 828-2017 测定。"]),
        summarizer=FakeListChatModel(
            responses=["<think>\nThe user is asking how to measure COD"]
        ),
        char_threshold=100000,
    )

    await svc.query(
        query=query_text,
        factor_name="化学需氧量",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )

    loaded = await store.get(session_id)
    assert loaded is not None
    assert loaded.title == fallback_title(query_text)


@pytest.mark.asyncio
async def test_query_title_fallback_on_summarizer_failure():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = KnowledgeFactorQueryPayload(matched=False)
    query_text = "COD怎么测"
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["不应调用"]),
        summarizer=BrokenSummarizer(),
        char_threshold=100000,
    )
    await svc.query(
        query=query_text,
        factor_name="化学需氧量",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )
    loaded = await store.get(session_id)
    assert loaded is not None
    assert loaded.title == fallback_title(query_text)


@pytest.mark.asyncio
async def test_query_title_fallback_when_summarizer_returns_empty():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = KnowledgeFactorQueryPayload(matched=False)
    query_text = "今天适合吃什么？"
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["不应调用"]),
        summarizer=FakeListChatModel(responses=["   "]),
        rewrite_model=FakeListChatModel(
            responses=[
                _rewrite_response(
                    should_query_knowledge=False,
                    known_supported_factor=False,
                    rewritten_query="",
                    factor_name=None,
                    confidence=0.1,
                )
            ]
        ),
        char_threshold=100000,
    )
    await svc.query(
        query=query_text,
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )
    loaded = await store.get(session_id)
    assert loaded is not None
    assert loaded.title == fallback_title(query_text)
    assert loaded.title != ""
