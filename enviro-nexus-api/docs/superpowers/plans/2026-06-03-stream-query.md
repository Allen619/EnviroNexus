# 流式因子查询 API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改现有 `POST /api/v1/factors/query` 的前提下，新增 SSE 流式端点 `/api/v1/factors/query/stream`，通过重构 `ChatQueryService` 抽取共通逻辑供 sync/stream 双入口复用。

**Architecture:** 方案 1 — `_prepare_turn` / `_finalize_turn` 等私有方法承载会话加载、压缩、知识检索、落库；`query()` 走 `ainvoke`，`query_stream()` 走 `astream` 并按 meta → token → done 推送 SSE；流前错误抛现有异常返回 JSON，流中 LLM 失败推 `error` 事件且不落库。

**Tech Stack:** FastAPI (`StreamingResponse`), pydantic v2, langchain-core (`astream` / `FakeListChatModel`), pytest-asyncio, httpx `AsyncClient`

**Spec:** [`docs/superpowers/specs/2026-06-03-stream-query-design.md`](../specs/2026-06-03-stream-query-design.md)

---

## File Map

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `app/utils/sse.py` | `format_sse(event, data)` 格式化 SSE 帧 |
| Create | `app/schemas/stream_query.py` | SSE 事件 payload Pydantic 模型（测试/文档） |
| Modify | `app/services/chat_query_service.py` | `TurnContext`、共通方法、`query()` 重构、`query_stream()` |
| Modify | `app/api/v1/factors.py` | 新增 `POST /factors/query/stream` |
| Create | `tests/test_sse.py` | SSE 格式化单测 |
| Create | `tests/test_chat_query_stream.py` | Service 层流式单测 |
| Create | `tests/test_factors_stream.py` | API 层流式集成测试 |
| Modify | `README.md` | 流式端点说明与 curl 示例 |
| Modify | `docs/superpowers/specs/2026-06-03-stream-query-design.md` | 状态改为「已评审」 |

---

### Task 1: SSE 格式化工具

**Files:**
- Create: `app/utils/sse.py`
- Create: `tests/test_sse.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_sse.py
import json

from app.utils.sse import format_sse


def test_format_sse_produces_valid_frame():
    frame = format_sse("meta", {"session_id": "s1", "matched": True})
    assert frame.startswith("event: meta\n")
    assert "data: " in frame
    assert frame.endswith("\n\n")
    data_line = [ln for ln in frame.split("\n") if ln.startswith("data:")][0]
    payload = json.loads(data_line.removeprefix("data: ").strip())
    assert payload["session_id"] == "s1"
    assert payload["matched"] is True


def test_format_sse_serializes_nested_sources():
    frame = format_sse("token", {"content": "你好"})
    data_line = [ln for ln in frame.split("\n") if ln.startswith("data:")][0]
    assert json.loads(data_line.removeprefix("data: ").strip()) == {"content": "你好"}
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `uv run pytest tests/test_sse.py -v`  
Expected: FAIL — `ModuleNotFoundError: app.utils.sse`

- [ ] **Step 3: 实现 `app/utils/sse.py`**

```python
import json
from typing import Any


def format_sse(event: str, data: dict[str, Any]) -> str:
    """Format one Server-Sent Event frame (event + data + blank line)."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
```

- [ ] **Step 4: 运行 PASS**

Run: `uv run pytest tests/test_sse.py -v`  
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add app/utils/sse.py tests/test_sse.py
git commit -m "feat: add SSE format helper for stream query"
```

---

### Task 2: SSE 事件 Schema

**Files:**
- Create: `app/schemas/stream_query.py`
- Create: `tests/test_stream_query_schema.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_stream_query_schema.py
from app.schemas.stream_query import StreamDoneEvent, StreamMetaEvent, StreamTokenEvent


def test_stream_meta_event_fields():
    evt = StreamMetaEvent(
        session_id="s1",
        matched=True,
        factor="化学需氧量",
        matched_alias="COD",
        card_id="card_1",
        sources=[],
        code="OK",
    )
    assert evt.code == "OK"


def test_stream_token_event():
    assert StreamTokenEvent(content="片段").content == "片段"


def test_stream_done_event():
    evt = StreamDoneEvent(session_id="s1", reply="完整回复")
    assert evt.reply == "完整回复"
```

- [ ] **Step 2: 运行 FAIL**

Run: `uv run pytest tests/test_stream_query_schema.py -v`  
Expected: FAIL — module not found

- [ ] **Step 3: 创建 `app/schemas/stream_query.py`**

```python
from pydantic import BaseModel, Field

from app.schemas.chat_query import SourceItem


class StreamMetaEvent(BaseModel):
    session_id: str
    matched: bool
    factor: str | None = None
    matched_alias: str | None = None
    card_id: str | None = None
    sources: list[SourceItem] = Field(default_factory=list)
    code: str  # OK | FACTOR_NOT_FOUND


class StreamTokenEvent(BaseModel):
    content: str


class StreamDoneEvent(BaseModel):
    session_id: str
    reply: str


class StreamErrorEvent(BaseModel):
    code: str
    message: str
```

- [ ] **Step 4: 运行 PASS**

Run: `uv run pytest tests/test_stream_query_schema.py -v`  
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/schemas/stream_query.py tests/test_stream_query_schema.py
git commit -m "feat: add SSE event payload schemas for stream query"
```

---

### Task 3: ChatQueryService 重构（共通 prep + sync 入口）

**Files:**
- Modify: `app/services/chat_query_service.py`

本 Task **不新增** `query_stream`，仅抽取共通方法并让现有 `query()` 调用它们。完成后现有单测应全部通过。

- [ ] **Step 1: 在 `chat_query_service.py` 顶部增加 import 与 TurnContext**

在现有 import 区追加：

```python
import json
from dataclasses import dataclass

from app.utils.sse import format_sse
from app.schemas.stream_query import StreamMetaEvent
```

在 `FACTOR_NOT_FOUND_MESSAGE` 之后、`class ChatQueryService` 之前追加：

```python
@dataclass
class TurnContext:
    record: SessionRecord
    payload: KnowledgeFactorQueryPayload
    sources: list[SourceItem]
    llm_messages: list[SystemMessage | HumanMessage]
    query: str
```

- [ ] **Step 2: 在 `ChatQueryService` 内新增共通私有方法**

在 `_maybe_generate_title` 之后、`async def query` 之前插入：

```python
def _build_llm_messages(
    self,
    record: SessionRecord,
    payload: KnowledgeFactorQueryPayload,
    query: str,
) -> list[SystemMessage | HumanMessage]:
    knowledge_block = build_knowledge_block(payload)
    history = "\n".join(f"{m.role}: {m.content}" for m in record.messages)
    summary_part = f"【会话摘要】\n{record.summary}\n" if record.summary else ""
    return [
        SystemMessage(content=REPLY_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"{summary_part}【最近对话】\n{history}\n\n"
                f"{knowledge_block}\n\n【用户问题】\n{query}"
            )
        ),
    ]

async def _prepare_turn(
    self, query: str, session_id: str, user_id: str
) -> TurnContext:
    record = await self._load_session(session_id, user_id)
    await self._compressor.maybe_compress(record)
    try:
        payload = await self._knowledge.query_factor(query)
    except (httpx.HTTPError, ValueError):
        logger.exception("knowledge query failed: query=%s", query)
        raise KnowledgeServiceError("知识服务调用失败，请稍后重试")
    sources = self._map_sources(payload)
    llm_messages = self._build_llm_messages(record, payload, query)
    return TurnContext(
        record=record,
        payload=payload,
        sources=sources,
        llm_messages=llm_messages,
        query=query,
    )

def _build_meta_payload(self, ctx: TurnContext) -> dict:
    code = "OK" if ctx.payload.matched else "FACTOR_NOT_FOUND"
    event = StreamMetaEvent(
        session_id=ctx.record.session_id,
        matched=ctx.payload.matched,
        factor=ctx.payload.factor,
        matched_alias=ctx.payload.matched_alias,
        card_id=ctx.payload.card_id,
        sources=ctx.sources,
        code=code,
    )
    return event.model_dump(mode="json")

async def _collect_llm_reply(
    self, messages: list[SystemMessage | HumanMessage]
) -> str:
    try:
        resp = await self._chat.ainvoke(messages)
    except Exception:
        logger.exception("llm invoke failed")
        raise LLMServiceError("大模型服务调用失败，请稍后重试")
    content = resp.content
    return content if isinstance(content, str) else str(content)

async def _stream_llm_tokens(
    self, messages: list[SystemMessage | HumanMessage]
):
    async for chunk in self._chat.astream(messages):
        content = chunk.content
        if content:
            text = content if isinstance(content, str) else str(content)
            yield text

async def _finalize_turn(self, ctx: TurnContext, reply: str) -> None:
    ctx.record.messages.append(ChatMessage(role="user", content=ctx.query))
    ctx.record.messages.append(
        ChatMessage(role="assistant", content=reply, sources=ctx.sources)
    )
    ctx.record.updated_at = datetime.now(timezone.utc)
    await self._maybe_generate_title(ctx.record)
    await self._store.save(ctx.record)
```

- [ ] **Step 3: 重写 `query()` 使用共通方法**

将现有 `query()` 方法体替换为：

```python
async def query(
    self,
    query: str,
    request_id: str | None,
    session_id: str,
    user_id: str,
) -> FactorQueryResponse:
    ctx = await self._prepare_turn(query, session_id, user_id)

    if not ctx.payload.matched:
        reply = NOT_MATCHED_REPLY_FALLBACK
        code = "FACTOR_NOT_FOUND"
        message = FACTOR_NOT_FOUND_MESSAGE
    else:
        reply = await self._collect_llm_reply(ctx.llm_messages)
        code = "OK"
        message = "查询成功"

    await self._finalize_turn(ctx, reply)

    return FactorQueryResponse(
        success=True,
        code=code,
        message=message,
        request_id=request_id,
        data=FactorQueryData(
            session_id=ctx.record.session_id,
            matched=ctx.payload.matched,
            reply=reply,
            factor=ctx.payload.factor,
            matched_alias=ctx.payload.matched_alias,
            card_id=ctx.payload.card_id,
            sources=ctx.sources,
            warnings=[],
        ),
        timestamp=datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: 运行回归测试**

Run: `uv run pytest tests/test_chat_query_service.py -v`  
Expected: 全部 passed（行为与重构前一致）

- [ ] **Step 5: Commit**

```bash
git add app/services/chat_query_service.py
git commit -m "refactor: extract shared turn prep/finalize in ChatQueryService"
```

---

### Task 4: `query_stream()` Service 实现（TDD）

**Files:**
- Modify: `app/services/chat_query_service.py`
- Create: `tests/test_chat_query_stream.py`

- [ ] **Step 1: 写失败测试（含 SSE 解析 helper 与分块 Fake LLM）**

```python
# tests/test_chat_query_stream.py
import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from app.llm.prompts import NOT_MATCHED_REPLY_FALLBACK
from app.schemas.knowledge import KnowledgeFactorQueryPayload
from app.schemas.session import SessionRecord
from app.services.chat_query_service import ChatQueryService
from app.services.session_store import InMemorySessionStore
from tests.test_chat_query_service import _create_session, _matched_payload


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
```

- [ ] **Step 2: 运行 FAIL**

Run: `uv run pytest tests/test_chat_query_stream.py -v`  
Expected: FAIL — `query_stream` 不存在

- [ ] **Step 3: 在 `ChatQueryService` 追加 `query_stream()`**

在 `query()` 方法之后追加：

```python
async def query_stream(
    self,
    query: str,
    session_id: str,
    user_id: str,
):
    from app.schemas.stream_query import StreamDoneEvent, StreamErrorEvent, StreamTokenEvent

    ctx = await self._prepare_turn(query, session_id, user_id)
    yield format_sse("meta", self._build_meta_payload(ctx))

    if not ctx.payload.matched:
        reply = NOT_MATCHED_REPLY_FALLBACK
        yield format_sse("token", StreamTokenEvent(content=reply).model_dump(mode="json"))
    else:
        reply_parts: list[str] = []
        try:
            async for chunk in self._stream_llm_tokens(ctx.llm_messages):
                reply_parts.append(chunk)
                yield format_sse(
                    "token", StreamTokenEvent(content=chunk).model_dump(mode="json")
                )
        except Exception:
            logger.exception("llm stream failed")
            yield format_sse(
                "error",
                StreamErrorEvent(
                    code="LLM_SERVICE_ERROR",
                    message="大模型服务调用失败，请稍后重试",
                ).model_dump(mode="json"),
            )
            return
        reply = "".join(reply_parts)

    await self._finalize_turn(ctx, reply)
    yield format_sse(
        "done",
        StreamDoneEvent(
            session_id=ctx.record.session_id,
            reply=reply,
        ).model_dump(mode="json"),
    )
```

- [ ] **Step 4: 运行 PASS**

Run: `uv run pytest tests/test_chat_query_stream.py tests/test_chat_query_service.py -v`  
Expected: 全部 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/chat_query_service.py tests/test_chat_query_stream.py
git commit -m "feat: add query_stream SSE generator to ChatQueryService"
```

---

### Task 5: 流式 API 路由（TDD）

**Files:**
- Modify: `app/api/v1/factors.py`
- Create: `tests/test_factors_stream.py`

- [ ] **Step 1: 写失败集成测试**

```python
# tests/test_factors_stream.py
import json
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import DEFAULT_USER_HEADERS

STREAM_BODY = {"query": "COD 怎么测？", "session_id": "stream-session-1"}


def parse_sse_events(raw: str) -> list[tuple[str, dict]]:
    events = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = "message"
        data = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data = json.loads(line.removeprefix("data:").strip())
        if data is not None:
            events.append((event_type, data))
    return events


@pytest.mark.asyncio
async def test_factor_query_stream_returns_sse(client):
    async def fake_stream(*args, **kwargs):
        yield "event: meta\ndata: {\"session_id\":\"s1\",\"matched\":true,\"code\":\"OK\",\"sources\":[]}\n\n"
        yield "event: token\ndata: {\"content\":\"你好\"}\n\n"
        yield "event: done\ndata: {\"session_id\":\"s1\",\"reply\":\"你好\"}\n\n"

    with patch(
        "app.services.chat_query_service.ChatQueryService.query_stream",
        side_effect=fake_stream,
    ):
        resp = await client.post(
            "/api/v1/factors/query/stream",
            headers=DEFAULT_USER_HEADERS,
            json=STREAM_BODY,
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = parse_sse_events(resp.text)
    assert [t for t, _ in events] == ["meta", "token", "done"]


@pytest.mark.asyncio
async def test_factor_query_stream_missing_user_id_422_json(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        json=STREAM_BODY,
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_factor_query_stream_blank_query_422(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        headers=DEFAULT_USER_HEADERS,
        json={"query": "   ", "session_id": "s1"},
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")
```

- [ ] **Step 2: 运行 FAIL**

Run: `uv run pytest tests/test_factors_stream.py -v`  
Expected: FAIL — 404 Not Found

- [ ] **Step 3: 修改 `app/api/v1/factors.py`**

在文件顶部 import 区追加：

```python
from fastapi.responses import StreamingResponse
```

在 `query_factor` 路由之后追加：

```python
@router.post(
    "/factors/query/stream",
    responses={
        200: {
            "description": "SSE 流式响应（text/event-stream）；流前错误仍为 JSON",
            "content": {"text/event-stream": {}},
        },
        **COMMON_RESPONSES,
    },
    summary="会话内因子查询（流式）",
)
async def query_factor_stream(
    body: FactorQueryRequest,
    chat_service: ChatQueryService = Depends(get_chat_query_service_dep),
    user_id: str = Depends(get_user_id),
):
    """与 `POST /factors/query` 相同请求体与鉴权；响应为 SSE。

    事件顺序：`meta`（sources 等）→ `token`（回复片段）→ `done`。
    流前校验/会话/知识失败返回 JSON 错误；流中 LLM 失败推送 `error` 事件。
    """
    return StreamingResponse(
        chat_service.query_stream(
            query=body.query,
            session_id=body.session_id,
            user_id=user_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: 运行 PASS + 全量回归**

Run: `uv run pytest tests/test_factors_stream.py tests/test_factors.py tests/test_chat_query_service.py tests/test_chat_query_stream.py -v`  
Expected: 全部 passed

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/factors.py tests/test_factors_stream.py
git commit -m "feat: add POST /factors/query/stream SSE endpoint"
```

---

### Task 6: 文档更新

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-06-03-stream-query-design.md`

- [ ] **Step 1: 更新 README 会话 API 表格**

在「多轮会话 API」表格中 `POST /api/v1/factors/query` 行之后追加：

```markdown
| `POST` | `/api/v1/factors/query/stream` | 同上请求体；SSE 流式返回（`meta` → `token` → `done`） |
```

在 curl 示例之后追加：

```bash
# 流式查询（SSE）
curl -N -X POST http://localhost:8080/api/v1/factors/query/stream \
  -H "X-User-Id: user-001" -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","query":"COD 怎么测？"}'
```

并追加一句：设计细节见 `docs/superpowers/specs/2026-06-03-stream-query-design.md`。

- [ ] **Step 2: 更新 spec 状态**

将 `docs/superpowers/specs/2026-06-03-stream-query-design.md` 首行状态改为：

```markdown
**状态**：已评审（brainstorming + implementation plan 已确认）
```

- [ ] **Step 3: 全量测试**

Run: `uv run pytest -v`  
Expected: 全部 passed

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/specs/2026-06-03-stream-query-design.md
git commit -m "docs: document stream query SSE endpoint"
```

---

## Spec Coverage Checklist

| Spec 要求 | Task |
|-----------|------|
| 新增 `/factors/query/stream`，不改现有 query | Task 5 |
| SSE meta → token → done 顺序 | Task 4 |
| meta 含 sources/matched/code | Task 3, 4 |
| 未命中走 FACTOR_NOT_FOUND + fallback token | Task 4 |
| 流前错误 JSON（422/404/502） | Task 5（422）；404/502 沿用现有异常链 |
| 流中 LLM 失败 error + 不落库 | Task 4 |
| 方案 1 共通 prep + 双入口 | Task 3, 4 |
| `_finalize_turn` 含标题生成与落库 | Task 3 |
| Cache-Control / X-Accel-Buffering | Task 5 |
| 回归现有 sync 测试 | Task 3, 5 |
| README 文档 | Task 6 |

---

## 验证命令（完成全部 Task 后）

```bash
cd D:\project_all\enviro-nexus-api
uv run pytest -v
```

手动冒烟：

```bash
uv run uvicorn app.main:app --port 8080

# 创建会话
curl -s -X POST http://localhost:8080/api/v1/sessions -H "X-User-Id: demo-user"

# 流式查询（替换 SESSION_ID）
curl -N -X POST http://localhost:8080/api/v1/factors/query/stream \
  -H "Content-Type: application/json" \
  -H "X-User-Id: demo-user" \
  -d "{\"query\":\"COD怎么测？\",\"session_id\":\"SESSION_ID\"}"
```

预期输出含 `event: meta`、`event: token`（若干）、`event: done`。
