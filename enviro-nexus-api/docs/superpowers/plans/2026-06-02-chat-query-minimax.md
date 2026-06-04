# 会话式因子查询（LangChain + MiniMax-M3）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `POST /api/v1/factors/query` 升级为带会话、上下文压缩、知识检索 + MiniMax 自然语言回复，并返回 `sources`（evidence_refs）。

**Architecture:** 固定流水线 `ChatQueryService`：SessionStore → ContextCompressor → KnowledgeClient（必调）→ LangChain ChatOpenAI（MiniMax）→ 落库会话。`sources` 仅来自 knowledge，不来自模型。

**Tech Stack:** FastAPI, httpx, pydantic-settings, langchain-core, langchain-openai（MiniMax OpenAI 兼容）, redis（可选）, pytest-asyncio

**Spec:** [`docs/superpowers/specs/2026-06-02-chat-query-minimax-design.md`](../specs/2026-06-02-chat-query-minimax-design.md)

---

## File Map（实施前总览）

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `app/schemas/chat_query.py` | 会话式 query 请求/响应、`SourceItem` |
| Create | `app/schemas/session.py` | `SessionRecord`、`ChatMessage` |
| Create | `app/services/session_store.py` | `SessionStore` 协议 + Memory + Redis |
| Create | `app/services/context_compressor.py` | 摘要缓冲压缩 |
| Create | `app/services/chat_query_service.py` | 主编排 |
| Create | `app/llm/minimax_chat.py` | `get_chat_model()` |
| Create | `app/llm/prompts.py` | 系统/检索/摘要 Prompt 模板 |
| Create | `tests/test_session_store.py` | 会话存储单测 |
| Create | `tests/test_context_compressor.py` | 压缩单测 |
| Create | `tests/test_chat_query_service.py` | 编排单测（mock LLM） |
| Modify | `app/schemas/factor_query.py` | 请求加 `session_id`；`FactorQueryData` 改为 chat 形状 |
| Modify | `app/schemas/knowledge.py` | `KnowledgeEvidenceRefItem` 增加可选 `evidence_id`、`field_path` |
| Modify | `app/core/exceptions.py` | 新增 `LLMServiceError` |
| Modify | `app/config/settings.py` | MiniMax + Session 配置项 |
| Modify | `app/dependencies.py` | `get_chat_query_service_dep` |
| Modify | `app/api/v1/factors.py` | 路由改调 `ChatQueryService` |
| Modify | `app/services/factor_service.py` | **删除** `query_factor`，保留 `get_method_card` |
| Modify | `tests/test_factors.py` | 新响应契约 + 502/多轮 |
| Modify | `pyproject.toml`、`.env.example`、`README.md`、`poc.md` | 依赖与文档 |

---

### Task 1: 添加 Python 依赖

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`（运行 uv lock 生成）

- [ ] **Step 1: 修改 `pyproject.toml` dependencies**

在 `dependencies` 数组追加：

```toml
    "langchain-core>=0.3.0",
    "langchain-openai>=0.2.0",
    "redis>=5.0.0",
```

- [ ] **Step 2: 安装并锁定**

Run: `cd D:\project_all\enviro-nexus-api && uv sync`  
Expected: 成功，无解析错误

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add langchain and redis dependencies"
```

---

### Task 2: 配置项与 LLM 异常

**Files:**
- Modify: `app/config/settings.py`
- Modify: `app/core/exceptions.py`
- Modify: `.env.example`

- [ ] **Step 1: 扩展 Settings**

在 `app/config/settings.py` 的 `Settings` 类中、`log_level` 之后追加：

```python
    # MiniMax / LLM
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "MiniMax-M3"
    minimax_timeout: float = 60.0

    # Session
    session_store: str = "memory"  # memory | redis
    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 86400
    max_recent_turns: int = 6
    compress_char_threshold: int = 6000
```

- [ ] **Step 2: 新增 `LLMServiceError`**

在 `app/core/exceptions.py` 的 `KnowledgeServiceError` 之后追加：

```python
class LLMServiceError(AppError):
    """大模型调用失败。"""

    def __init__(self, message: str = "大模型服务调用失败"):
        super().__init__(message=message, status_code=502, code="LLM_SERVICE_ERROR")
```

- [ ] **Step 3: 更新 `.env.example`**

追加 spec 第 7 节全部变量（`MINIMAX_*`、`SESSION_*`、`REDIS_URL`）。

- [ ] **Step 4: Commit**

```bash
git add app/config/settings.py app/core/exceptions.py .env.example
git commit -m "feat: add MiniMax and session settings, LLMServiceError"
```

---

### Task 3: Chat Query Schema（TDD 先写契约测试）

**Files:**
- Create: `app/schemas/chat_query.py`
- Modify: `app/schemas/factor_query.py`
- Modify: `tests/test_factors.py`（先改失败测试，Task 10 完整化）

- [ ] **Step 1: 创建 `app/schemas/chat_query.py`**

```python
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
```

- [ ] **Step 2: 精简 `app/schemas/factor_query.py`**

- 删除 `FactorQueryRequest`、`FactorQueryData`、`FactorQueryResponse`。
- 保留 `RequirementItem`、`EvidenceRefItem`、`FactorAnswer`（供 knowledge 映射或删除若仅 knowledge.py 使用 — 当前 `knowledge.py` 引用 `FactorAnswer`，可保留或把 `to_factor_answer` 移到 chat 层；**最小改动**：保留 `FactorAnswer` 等，仅移除 query 相关）。
- `MethodCard*` 与 `MethodCardResponse` 不变。

- [ ] **Step 3: 扩展 knowledge evidence 字段**

在 `app/schemas/knowledge.py` 的 `KnowledgeEvidenceRefItem` 追加：

```python
    evidence_id: str | None = None
    field_path: str | None = None
```

- [ ] **Step 4: 更新 `app/api/v1/factors.py` 导入**

```python
from app.schemas.chat_query import FactorQueryRequest, FactorQueryResponse
from app.schemas.factor_query import MethodCardResponse
```

（`MethodCardResponse` 仍在 `factor_query.py`）

- [ ] **Step 5: Commit**

```bash
git add app/schemas/chat_query.py app/schemas/factor_query.py app/schemas/knowledge.py app/api/v1/factors.py
git commit -m "feat: add chat query schemas and extend evidence fields"
```

---

### Task 4: Session 模型与 InMemorySessionStore（TDD）

**Files:**
- Create: `app/schemas/session.py`
- Create: `app/services/session_store.py`
- Create: `tests/test_session_store.py`

- [ ] **Step 1: 写失败测试 `tests/test_session_store.py`**

```python
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.session import ChatMessage, SessionRecord
from app.services.session_store import InMemorySessionStore


@pytest.mark.asyncio
async def test_save_and_get_roundtrip():
    store = InMemorySessionStore(ttl_seconds=3600)
    record = SessionRecord(
        session_id="s1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        summary="",
        messages=[ChatMessage(role="user", content="hi")],
    )
    await store.save(record)
    loaded = await store.get("s1")
    assert loaded is not None
    assert loaded.messages[0].content == "hi"


@pytest.mark.asyncio
async def test_expired_session_returns_none():
    store = InMemorySessionStore(ttl_seconds=1)
    record = SessionRecord(
        session_id="s2",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        updated_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        summary="",
        messages=[],
    )
    await store.save(record)
    assert await store.get("s2") is None
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `uv run pytest tests/test_session_store.py -v`  
Expected: `ModuleNotFoundError` 或 `ImportError`

- [ ] **Step 3: 实现 `app/schemas/session.py`**

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class SessionRecord(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    summary: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
```

- [ ] **Step 4: 实现 `app/services/session_store.py`**

```python
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Protocol

from app.schemas.session import SessionRecord


class SessionStore(ABC):
    @abstractmethod
    async def get(self, session_id: str) -> SessionRecord | None: ...

    @abstractmethod
    async def save(self, record: SessionRecord) -> None: ...


class InMemorySessionStore(SessionStore):
    def __init__(self, ttl_seconds: int = 86400) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, SessionRecord] = {}

    def _is_expired(self, record: SessionRecord) -> bool:
        now = datetime.now(timezone.utc)
        age = (now - record.updated_at).total_seconds()
        return age > self._ttl

    async def get(self, session_id: str) -> SessionRecord | None:
        record = self._data.get(session_id)
        if record is None:
            return None
        if self._is_expired(record):
            del self._data[session_id]
            return None
        return record

    async def save(self, record: SessionRecord) -> None:
        self._data[record.session_id] = record


def build_session_store(store_type: str, ttl_seconds: int, redis_url: str) -> SessionStore:
    if store_type == "redis":
        return RedisSessionStore(redis_url=redis_url, ttl_seconds=ttl_seconds)
    return InMemorySessionStore(ttl_seconds=ttl_seconds)


class RedisSessionStore(SessionStore):
    """Task 11 实现；此处先 raise 或留空类 stub — Task 4 仅 Memory。"""

    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        raise NotImplementedError("RedisSessionStore implemented in Task 11")
```

**Task 4 仅提交 Memory 版本**；`build_session_store` 在 Task 11 前只对 `memory` 分支可用：

```python
def build_session_store(store_type: str, ttl_seconds: int, redis_url: str) -> SessionStore:
    if store_type == "redis":
        raise NotImplementedError("redis session store not yet enabled")
    return InMemorySessionStore(ttl_seconds=ttl_seconds)
```

- [ ] **Step 5: 运行测试 PASS**

Run: `uv run pytest tests/test_session_store.py -v`  
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add app/schemas/session.py app/services/session_store.py tests/test_session_store.py
git commit -m "feat: add in-memory session store"
```

---

### Task 5: ContextCompressor（TDD）

**Files:**
- Create: `app/services/context_compressor.py`
- Create: `tests/test_context_compressor.py`

- [ ] **Step 1: 写失败测试**

```python
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.schemas.session import ChatMessage, SessionRecord
from app.services.context_compressor import ContextCompressor


@pytest.mark.asyncio
async def test_compress_moves_old_messages_into_summary():
    summarizer = FakeListChatModel(responses=["用户问过COD"])
    compressor = ContextCompressor(
        summarizer=summarizer,
        max_recent_messages=2,
        char_threshold=10,
    )
    record = SessionRecord(
        session_id="s1",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        summary="",
        messages=[
            ChatMessage(role="user", content="old1"),
            ChatMessage(role="assistant", content="old2"),
            ChatMessage(role="user", content="recent"),
        ],
    )
    await compressor.maybe_compress(record)
    assert "COD" in record.summary or record.summary != ""
    assert len(record.messages) <= 2
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `uv run pytest tests/test_context_compressor.py -v`

- [ ] **Step 3: 实现 `app/services/context_compressor.py`**

```python
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas.session import SessionRecord

SUMMARY_SYSTEM = "你是会话摘要助手。只归纳用户问过什么、助手已确认的事实。不要编造标准号。输出简短中文段落。"


class ContextCompressor:
    def __init__(
        self,
        summarizer: BaseChatModel,
        max_recent_messages: int = 6,
        char_threshold: int = 6000,
    ) -> None:
        self._summarizer = summarizer
        self._max_recent = max_recent_messages
        self._char_threshold = char_threshold

    def _estimate_chars(self, record: SessionRecord) -> int:
        total = len(record.summary)
        for m in record.messages:
            total += len(m.content)
        return total

    async def maybe_compress(self, record: SessionRecord) -> None:
        if len(record.messages) <= self._max_recent and self._estimate_chars(record) <= self._char_threshold:
            return
        to_summarize = record.messages[: -self._max_recent] if len(record.messages) > self._max_recent else []
        if not to_summarize and self._estimate_chars(record) <= self._char_threshold:
            return
        if not to_summarize:
            return
        blob = "\n".join(f"{m.role}: {m.content}" for m in to_summarize)
        prior = record.summary or "（无）"
        resp = await self._summarizer.ainvoke(
            [
                SystemMessage(content=SUMMARY_SYSTEM),
                HumanMessage(content=f"已有摘要：{prior}\n\n待摘要对话：\n{blob}"),
            ]
        )
        record.summary = resp.content if isinstance(resp.content, str) else str(resp.content)
        record.messages = record.messages[-self._max_recent :]
```

- [ ] **Step 4: 运行 PASS**

Run: `uv run pytest tests/test_context_compressor.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/services/context_compressor.py tests/test_context_compressor.py
git commit -m "feat: add context compressor with summary buffer"
```

---

### Task 6: MiniMax LangChain 封装

**Files:**
- Create: `app/llm/minimax_chat.py`
- Create: `app/llm/prompts.py`

- [ ] **Step 1: 创建 `app/llm/prompts.py`**

```python
REPLY_SYSTEM_PROMPT = """你是环检智枢的环保检测标准方法助手。
仅根据【本轮知识库检索】与【会话摘要】中的事实用简体中文回答。
若 matched 为 false，说明知识库未收录，不要编造标准号或方法细节。
正文不要伪造引用编号；依据由接口 sources 字段提供。"""

NOT_MATCHED_REPLY_FALLBACK = "当前知识库暂未收录该检测因子，请人工确认后再使用。"


def build_knowledge_block(payload) -> str:
    """payload: KnowledgeFactorQueryPayload"""
    if not payload.matched:
        return "【本轮知识库检索】\nmatched: false"
    ans = payload.answer
    lines = [
        "【本轮知识库检索】",
        f"matched: true",
        f"factor: {payload.factor}",
        f"card_id: {payload.card_id}",
    ]
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
        for r in ans.requirements:
            lines.append(f"要求[{r.type}] {r.title}: {r.content}")
        for e in ans.evidence_refs:
            lines.append(
                f"依据: {e.source_title} / {e.section} / {e.summary} / {e.field_path}"
            )
    return "\n".join(lines)
```

- [ ] **Step 2: 创建 `app/llm/minimax_chat.py`**

```python
from langchain_openai import ChatOpenAI

from app.config.settings import Settings


def get_chat_model(settings: Settings, *, temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.minimax_model,
        api_key=settings.minimax_api_key or None,
        base_url=settings.minimax_base_url,
        temperature=temperature,
        timeout=settings.minimax_timeout,
    )


def get_summarizer_model(settings: Settings) -> ChatOpenAI:
    return get_chat_model(settings, temperature=0.0)
```

- [ ] **Step 3: Commit**

```bash
git add app/llm/prompts.py app/llm/minimax_chat.py
git commit -m "feat: add MiniMax LangChain client and prompts"
```

---

### Task 7: ChatQueryService（TDD，mock LLM）

**Files:**
- Create: `app/services/chat_query_service.py`
- Create: `tests/test_chat_query_service.py`

- [ ] **Step 1: 写失败集成测试（mock client + mock LLM）**

`tests/test_chat_query_service.py` 核心用例：

```python
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from unittest.mock import AsyncMock

from app.schemas.knowledge import KnowledgeFactorQueryPayload, KnowledgeFactorAnswer, KnowledgeEvidenceRefItem
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
```

再加 `test_not_matched_still_appends_session`（`matched=False`，`sources==[]`，`code==FACTOR_NOT_FOUND`）。

- [ ] **Step 2: 运行 FAIL**

Run: `uv run pytest tests/test_chat_query_service.py -v`

- [ ] **Step 3: 实现 `app/services/chat_query_service.py`**

要点（完整实现时包含）：

```python
import logging
import uuid
from datetime import datetime, timezone

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

import httpx

from app.clients.knowledge_client import KnowledgeClient
from app.core.exceptions import KnowledgeServiceError, LLMServiceError
from app.llm.prompts import NOT_MATCHED_REPLY_FALLBACK, REPLY_SYSTEM_PROMPT, build_knowledge_block
from app.schemas.chat_query import FactorQueryData, FactorQueryResponse, SourceItem
from app.schemas.knowledge import KnowledgeFactorQueryPayload
from app.schemas.session import ChatMessage, SessionRecord
from app.services.context_compressor import ContextCompressor
from app.services.session_store import SessionStore

logger = logging.getLogger(__name__)
SESSION_EXPIRED_WARNING = "会话已过期，已开启新会话。"


class ChatQueryService:
    def __init__(
        self,
        knowledge_client: KnowledgeClient,
        session_store: SessionStore,
        chat_model: BaseChatModel,
        summarizer: BaseChatModel,
        max_recent_messages: int = 6,
        char_threshold: int = 6000,
    ) -> None:
        self._knowledge = knowledge_client
        self._store = session_store
        self._chat = chat_model
        self._compressor = ContextCompressor(summarizer, max_recent_messages, char_threshold)

    def _map_sources(self, payload: KnowledgeFactorQueryPayload) -> list[SourceItem]:
        if not payload.answer:
            return []
        return [
            SourceItem(
                evidence_id=e.evidence_id,
                source_title=e.source_title,
                section=e.section,
                summary=e.summary,
                field_path=e.field_path,
            )
            for e in payload.answer.evidence_refs
        ]

    async def query(
        self,
        query: str,
        request_id: str | None,
        session_id: str | None,
    ) -> FactorQueryResponse:
        warnings: list[str] = []
        record: SessionRecord | None = None
        new_session = False

        if session_id:
            record = await self._store.get(session_id)
            if record is None:
                warnings.append(SESSION_EXPIRED_WARNING)
                new_session = True
        else:
            new_session = True

        if record is None:
            now = datetime.now(timezone.utc)
            sid = str(uuid.uuid4())
            record = SessionRecord(session_id=sid, created_at=now, updated_at=now)
        elif new_session:
            now = datetime.now(timezone.utc)
            record = SessionRecord(session_id=str(uuid.uuid4()), created_at=now, updated_at=now)

        await self._compressor.maybe_compress(record)

        try:
            payload = await self._knowledge.query_factor(query)
        except (httpx.HTTPError, ValueError):
            logger.exception("knowledge query failed")
            raise KnowledgeServiceError("知识服务调用失败，请稍后重试")

        knowledge_block = build_knowledge_block(payload)
        history = "\n".join(f"{m.role}: {m.content}" for m in record.messages)
        summary_part = f"【会话摘要】\n{record.summary}\n" if record.summary else ""

        if not payload.matched:
            reply = NOT_MATCHED_REPLY_FALLBACK
            code = "FACTOR_NOT_FOUND"
            message = "当前知识库暂未收录该检测因子"
        else:
            try:
                resp = await self._chat.ainvoke(
                    [
                        SystemMessage(content=REPLY_SYSTEM_PROMPT),
                        HumanMessage(
                            content=f"{summary_part}【最近对话】\n{history}\n\n{knowledge_block}\n\n【用户问题】\n{query}"
                        ),
                    ]
                )
                reply = resp.content if isinstance(resp.content, str) else str(resp.content)
            except Exception:
                logger.exception("llm invoke failed")
                raise LLMServiceError("大模型服务调用失败，请稍后重试")
            code = "OK"
            message = "查询成功"

        record.messages.append(ChatMessage(role="user", content=query))
        record.messages.append(ChatMessage(role="assistant", content=reply))
        record.updated_at = datetime.now(timezone.utc)
        await self._store.save(record)

        return FactorQueryResponse(
            success=True,
            code=code,
            message=message,
            request_id=request_id,
            data=FactorQueryData(
                session_id=record.session_id,
                matched=payload.matched,
                reply=reply,
                factor=payload.factor,
                matched_alias=payload.matched_alias,
                card_id=payload.card_id,
                sources=self._map_sources(payload),
                warnings=warnings,
            ),
            timestamp=datetime.now(timezone.utc),
        )
```

- [ ] **Step 4: 运行 PASS**

Run: `uv run pytest tests/test_chat_query_service.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/services/chat_query_service.py tests/test_chat_query_service.py
git commit -m "feat: add ChatQueryService with session and LLM reply"
```

---

### Task 8: 路由、依赖注入，移除旧 query_factor

**Files:**
- Modify: `app/dependencies.py`
- Modify: `app/api/v1/factors.py`
- Modify: `app/services/factor_service.py`

- [ ] **Step 1: `dependencies.py` 增加**

```python
from app.config.settings import Settings, get_settings
from app.llm.minimax_chat import get_chat_model, get_summarizer_model
from app.services.chat_query_service import ChatQueryService
from app.services.session_store import build_session_store

def get_chat_query_service(settings: Settings, knowledge_client: KnowledgeClient) -> ChatQueryService:
    store = build_session_store(
        settings.session_store,
        settings.session_ttl_seconds,
        settings.redis_url,
    )
    return ChatQueryService(
        knowledge_client=knowledge_client,
        session_store=store,
        chat_model=get_chat_model(settings),
        summarizer=get_summarizer_model(settings),
        max_recent_messages=settings.max_recent_turns,
        char_threshold=settings.compress_char_threshold,
    )

def get_chat_query_service_dep(
    http_client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> ChatQueryService:
    return get_chat_query_service(settings, get_knowledge_client(http_client, settings))
```

- [ ] **Step 2: 修改 `app/api/v1/factors.py` 的 query 端点**

```python
from app.dependencies import get_chat_query_service_dep, get_factor_service_dep
from app.services.chat_query_service import ChatQueryService

@router.post(...)
async def query_factor(
    body: FactorQueryRequest,
    request: Request,
    chat_service: ChatQueryService = Depends(get_chat_query_service_dep),
):
    request_id = getattr(request.state, "request_id", None)
    return await chat_service.query(
        query=body.query,
        request_id=request_id,
        session_id=body.session_id,
    )
```

`get_method_card` 仍用 `FactorService` + `get_factor_service_dep`。

- [ ] **Step 3: 从 `factor_service.py` 删除 `query_factor` 方法及仅其使用的 imports/constants**

- [ ] **Step 4: 运行全量测试**

Run: `uv run pytest -v`  
Expected: 若 `test_factors` 仍按旧 schema，会失败 — 进入 Task 9 修复

- [ ] **Step 5: Commit**

```bash
git add app/dependencies.py app/api/v1/factors.py app/services/factor_service.py
git commit -m "feat: wire ChatQueryService to factors query route"
```

---

### Task 9: 更新 API 集成测试

**Files:**
- Modify: `tests/test_factors.py`

- [ ] **Step 1: 重写 mock 目标为 `ChatQueryService.query`**

示例命中用例：

```python
from app.schemas.chat_query import FactorQueryData, FactorQueryResponse, SourceItem

mock_response = FactorQueryResponse(
    success=True,
    code="OK",
    message="查询成功",
    data=FactorQueryData(
        session_id="test-session",
        matched=True,
        reply="化学需氧量可采用 HJ 828-2017 测定。",
        factor="化学需氧量",
        card_id="water_cod_hj828_2017",
        sources=[
            SourceItem(source_title="HJ 828-2017", section="适用范围", summary="..."),
        ],
        warnings=[],
    ),
    timestamp="2026-06-02 08:00:00",
)

with patch(
    "app.services.chat_query_service.ChatQueryService.query",
    new_callable=AsyncMock,
    return_value=mock_response,
):
    ...
```

- [ ] **Step 2: 保留并调整**

- `test_factor_query_validation_422` — 仍测空 query
- `test_factor_query_knowledge_service_error_502` — patch `ChatQueryService.query` side_effect `KnowledgeServiceError`
- `test_factor_query_upstream_timeout_502` — patch `KnowledgeClient.query_factor` side_effect `httpx.TimeoutException`（走真实 DI 链）或 patch service
- 未命中：断言 `code == FACTOR_NOT_FOUND`、`reply`、`sources == []`
- 新增：`test_factor_query_returns_session_id` — 响应含 `data.session_id`

- [ ] **Step 3: 全量 PASS**

Run: `uv run pytest -v`  
Expected: 全部 passed

- [ ] **Step 4: Commit**

```bash
git add tests/test_factors.py
git commit -m "test: update factor query tests for chat response"
```

---

### Task 10: Redis SessionStore（可选，spec §4.2）

**Files:**
- Modify: `app/services/session_store.py`
- Create or extend: `tests/test_session_store.py`

- [ ] **Step 1: 实现 `RedisSessionStore`**

```python
import redis.asyncio as redis

class RedisSessionStore(SessionStore):
    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def get(self, session_id: str) -> SessionRecord | None:
        raw = await self._client.get(self._key(session_id))
        if not raw:
            return None
        return SessionRecord.model_validate_json(raw)

    async def save(self, record: SessionRecord) -> None:
        await self._client.set(
            self._key(record.session_id),
            record.model_dump_json(),
            ex=self._ttl,
        )
```

- [ ] **Step 2: 更新 `build_session_store` 启用 redis 分支**

- [ ] **Step 3: 单测用 `fakeredis`（可选）或标记 `@pytest.mark.integration` 跳过 CI**

- [ ] **Step 4: Commit**

```bash
git add app/services/session_store.py tests/test_session_store.py pyproject.toml
git commit -m "feat: add Redis session store"
```

---

### Task 11: 文档与 OpenAPI 说明

**Files:**
- Modify: `README.md`
- Modify: `poc.md` 第八节响应示例
- Modify: `app/api/v1/factors.py` 的 `responses` 文档字符串（已有 200 FACTOR_NOT_FOUND 说明则核对）

- [ ] **Step 1: README 增加 MiniMax 环境变量、会话说明、破坏性变更提示**

- [ ] **Step 2: `poc.md` 响应示例改为 `reply` + `sources` + `session_id`**

- [ ] **Step 3: Commit**

```bash
git add README.md poc.md
git commit -m "docs: update factor query API for chat sessions"
```

---

## Spec Coverage Checklist

| Spec 要求 | Task |
|-----------|------|
| 替代 `/factors/query` 契约 | Task 3, 8, 9 |
| session_id 自动生成/懒创建 | Task 4, 7 |
| 摘要缓冲压缩 | Task 5, 7 |
| 必调 knowledge | Task 7 |
| sources 来自 evidence_refs | Task 3, 7 |
| 未命中 FACTOR_NOT_FOUND | Task 7, 9 |
| LLMServiceError / KnowledgeServiceError | Task 2, 7 |
| MiniMax LangChain | Task 6, 7 |
| memory/redis 存储 | Task 4, 10 |
| 测试 | Task 4–5, 7, 9 |
| 保留 method-cards / health | Task 8（不改 health） |

---

## 验证命令（完成全部 Task 后）

```bash
cd D:\project_all\enviro-nexus-api
uv run pytest -v
uv run ruff check app tests   # 若项目已配置 ruff
```

手动冒烟（需 knowledge + MINIMAX_API_KEY）：

```bash
uv run uvicorn app.main:app --port 8080
curl -X POST http://localhost:8080/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"COD怎么测\"}"
```

第二轮带上返回的 `session_id`。

---

## 给前端团队的破坏性变更摘要

- 请求增加可选 `session_id`
- 响应 `data.answer` 移除 → `data.reply` + `data.sources` + `data.session_id`
- 未命中仍为 HTTP 200 + `FACTOR_NOT_FOUND`
