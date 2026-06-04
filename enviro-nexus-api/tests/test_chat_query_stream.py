import json
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from app.core.api_message import KNOWLEDGE_QUERY_NOT_MATCHED_REPLY
from app.llm.prompts import NOT_MATCHED_REPLY_FALLBACK
from app.schemas.knowledge import KnowledgeFactorQueryPayload
from app.services.chat_query_service import ChatQueryService
from app.services.session_store import InMemorySessionStore
from tests.test_chat_query_service import _create_session, _matched_payload, _rewrite_response


def parse_sse_events(raw: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = "message"
        data: dict[str, Any] | None = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data = json.loads(line.removeprefix("data:").strip())
        if data is not None:
            events.append((event_type, data))
    return events


class ChunkedFakeChatModel(BaseChatModel):
    """Yield fixed text chunks via astream for stream tests."""

    chunks: list[str]

    @property
    def _llm_type(self) -> str:
        return "chunked-fake"

    def _generate(self, *args, **kwargs):
        raise NotImplementedError

    async def _agenerate(self, *args, **kwargs):
        raise NotImplementedError

    async def _astream(self, *args, **kwargs) -> AsyncIterator[ChatGenerationChunk]:
        for piece in self.chunks:
            yield ChatGenerationChunk(message=AIMessageChunk(content=piece))


class BrokenStreamChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "broken-stream"

    def _generate(self, *args, **kwargs):
        raise NotImplementedError

    async def _agenerate(self, *args, **kwargs):
        raise NotImplementedError

    async def _astream(self, *args, **kwargs):
        if False:
            yield  # pragma: no cover
        raise RuntimeError("llm stream down")


async def _collect_stream(svc: ChatQueryService, **kwargs) -> str:
    parts: list[str] = []
    async for frame in svc.query_stream(**kwargs):
        parts.append(frame)
    return "".join(parts)


@pytest.mark.asyncio
async def test_query_stream_emits_meta_token_done():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=ChunkedFakeChatModel(chunks=["COD", "测定"]),
        summarizer=ChunkedFakeChatModel(chunks=["标题"]),
        char_threshold=100000,
    )
    raw = await _collect_stream(
        svc,
        query="COD怎么测",
        factor_name="化学需氧量",
        session_id=session_id,
        user_id=user_id,
    )
    events = parse_sse_events(raw)
    types = [t for t, _ in events]
    assert types == ["meta", "token", "token", "done"]
    meta = events[0][1]
    assert meta["matched"] is True
    assert meta["code"] == "OK"
    assert len(meta["sources"]) == 1
    assert events[1][1]["content"] == "COD"
    assert events[2][1]["content"] == "测定"
    assert events[3][1]["reply"] == "COD测定"
    loaded = await store.get(session_id)
    assert loaded is not None
    assert len(loaded.messages) == 2
    assert loaded.messages[1].content == "COD测定"
    knowledge.query_factor.assert_awaited_once_with("COD怎么测", "化学需氧量")


@pytest.mark.asyncio
async def test_query_stream_not_matched_emits_fallback_token():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = KnowledgeFactorQueryPayload(matched=False)
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=ChunkedFakeChatModel(chunks=["不应调用"]),
        summarizer=ChunkedFakeChatModel(chunks=["摘要"]),
        char_threshold=100000,
    )
    raw = await _collect_stream(
        svc,
        query="未知",
        factor_name="未知因子",
        session_id=session_id,
        user_id=user_id,
    )
    events = parse_sse_events(raw)
    assert events[0][0] == "meta"
    assert events[0][1]["code"] == "FACTOR_NOT_FOUND"
    assert events[1] == ("token", {"content": NOT_MATCHED_REPLY_FALLBACK})
    assert events[-1][0] == "done"


@pytest.mark.asyncio
async def test_query_stream_llm_failure_emits_error_without_persist():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=BrokenStreamChatModel(),
        summarizer=ChunkedFakeChatModel(chunks=["摘要"]),
        char_threshold=100000,
    )
    raw = await _collect_stream(
        svc,
        query="COD",
        factor_name="化学需氧量",
        session_id=session_id,
        user_id=user_id,
    )
    events = parse_sse_events(raw)
    assert events[0][0] == "meta"
    assert events[-1][0] == "error"
    assert events[-1][1]["code"] == "LLM_SERVICE_ERROR"
    loaded = await store.get(session_id)
    assert loaded is not None
    assert loaded.messages == []


@pytest.mark.asyncio
async def test_query_stream_returns_not_matched_when_rewriter_cannot_infer_factor():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=ChunkedFakeChatModel(chunks=["不应调用"]),
        summarizer=ChunkedFakeChatModel(chunks=["摘要"]),
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
    raw = await _collect_stream(
        svc,
        query="今天适合吃什么？",
        session_id=session_id,
        user_id=user_id,
    )
    events = parse_sse_events(raw)
    assert [t for t, _ in events] == ["meta", "token", "done"]
    assert events[0][1]["code"] == "FACTOR_NOT_FOUND"
    assert events[1] == ("token", {"content": KNOWLEDGE_QUERY_NOT_MATCHED_REPLY})
    assert events[2][1]["reply"] == KNOWLEDGE_QUERY_NOT_MATCHED_REPLY
    knowledge.query_factor.assert_not_called()
