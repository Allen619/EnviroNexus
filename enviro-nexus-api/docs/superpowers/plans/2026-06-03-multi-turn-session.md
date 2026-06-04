# 多轮会话管理 API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为前端多轮对话 UI 提供完整后端会话管理：显式创建/列表/详情/删除会话，`X-User-Id` 归属，无 TTL 持久化，改造 `POST /factors/query` 在已有会话内发消息并落库 `sources` 与 LLM 标题。

**Architecture:** 方案 A — `SessionService` 负责会话 CRUD 与标题生成；`ChatQueryService` 负责知识检索 + LLM 回复；`SessionStore` 扩展 `create` / `list_by_user` / `delete` 与用户索引；Memory/Redis 二选一、去掉 TTL。

**Tech Stack:** FastAPI, pydantic v2, langchain-core（FakeListChatModel 测试）, redis（可选）, pytest-asyncio

**Spec:** [`docs/superpowers/specs/2026-06-03-multi-turn-session-design.md`](../specs/2026-06-03-multi-turn-session-design.md)

---

## File Map（实施前总览）

| 操作 | 路径 | 职责 |
|------|------|------|
| Modify | `app/schemas/session.py` | 扩展 `SessionRecord`、`ChatMessage`；新增 `SessionSummary` |
| Create | `app/schemas/sessions_api.py` | 会话 API 请求/响应模型 |
| Modify | `app/schemas/chat_query.py` | `session_id` 必填；query strip 校验 |
| Modify | `app/services/session_store.py` | 去 TTL；`create` / `list_by_user` / `delete`；Redis 用户 ZSET |
| Create | `app/services/session_service.py` | 会话 CRUD、preview、标题生成 |
| Modify | `app/services/chat_query_service.py` | 用户校验、sources 落库、标题、取消懒创建 |
| Modify | `app/llm/prompts.py` | 标题生成 Prompt |
| Modify | `app/core/exceptions.py` | `SessionNotFoundError` |
| Modify | `app/dependencies.py` | `get_user_id`、`SessionService` 注入 |
| Create | `app/api/v1/sessions.py` | 四端点 CRUD |
| Modify | `app/api/v1/factors.py` | 接入 `X-User-Id` |
| Modify | `app/api/v1/router.py` | 注册 sessions 路由 |
| Modify | `app/main.py` | `build_session_store` 签名简化（去 ttl 传参） |
| Modify | `tests/test_session_store.py` | 去 TTL 测试；list/delete/create |
| Create | `tests/test_session_service.py` | SessionService 单测 |
| Create | `tests/test_sessions_api.py` | 会话 API 集成测试 |
| Modify | `tests/test_chat_query_service.py` | 新 query 契约 |
| Modify | `tests/test_factors.py` | `X-User-Id` + 必填 session_id |
| Modify | `tests/conftest.py` | 默认 header helper |
| Modify | `README.md`、`.env.example` | 文档与破坏性变更说明 |

---

### Task 1: Schema 扩展

**Files:**
- Modify: `app/schemas/session.py`
- Create: `app/schemas/sessions_api.py`
- Modify: `app/schemas/chat_query.py`

- [ ] **Step 1: 写失败测试 `tests/test_session_schema.py`**

```python
from datetime import datetime, timezone

from app.schemas.chat_query import SourceItem
from app.schemas.session import ChatMessage, SessionRecord, SessionSummary


def test_session_record_requires_user_id():
    record = SessionRecord(
        session_id="s1",
        user_id="user-a",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert record.user_id == "user-a"
    assert record.title == ""


def test_assistant_message_carries_sources():
    msg = ChatMessage(
        role="assistant",
        content="回复",
        sources=[SourceItem(source_title="HJ 828-2017")],
    )
    assert msg.sources[0].source_title == "HJ 828-2017"


def test_session_summary_preview():
    summary = SessionSummary(
        session_id="s1",
        title="COD咨询",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        preview="化学需氧量…",
        message_count=2,
    )
    assert summary.message_count == 2
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `uv run pytest tests/test_session_schema.py -v`  
Expected: FAIL（`user_id` / `SessionSummary` 不存在）

- [ ] **Step 3: 修改 `app/schemas/session.py`**

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chat_query import SourceItem


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str
    sources: list[SourceItem] = Field(default_factory=list)


class SessionRecord(BaseModel):
    session_id: str
    user_id: str
    title: str = ""
    created_at: datetime
    updated_at: datetime
    summary: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)


class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    preview: str = ""
    message_count: int = 0
```

- [ ] **Step 4: 创建 `app/schemas/sessions_api.py`**

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ApiResponse
from app.schemas.session import ChatMessage, SessionSummary


class SessionDetailData(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage] = Field(default_factory=list)


class SessionListData(BaseModel):
    items: list[SessionSummary]
    total: int
    page: int
    page_size: int


class SessionDeleteData(BaseModel):
    deleted: bool


SessionDetailResponse = ApiResponse[SessionDetailData]
SessionListResponse = ApiResponse[SessionListData]
SessionDeleteResponse = ApiResponse[SessionDeleteData]
```

- [ ] **Step 5: 修改 `app/schemas/chat_query.py`**

```python
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ApiResponse


class FactorQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    session_id: str = Field(..., min_length=1)

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
```

- [ ] **Step 6: 运行 PASS**

Run: `uv run pytest tests/test_session_schema.py -v`  
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add app/schemas/session.py app/schemas/sessions_api.py app/schemas/chat_query.py tests/test_session_schema.py
git commit -m "feat: extend session schemas for multi-turn session API"
```

---

### Task 2: SessionNotFoundError 与 X-User-Id 依赖

**Files:**
- Modify: `app/core/exceptions.py`
- Modify: `app/dependencies.py`
- Modify: `app/schemas/common.py`（404 响应声明）

- [ ] **Step 1: 新增异常**

在 `app/core/exceptions.py` 的 `LLMServiceError` 之后追加：

```python
class SessionNotFoundError(AppError):
    """会话不存在或不属于当前用户。"""

    def __init__(self, message: str = "会话不存在"):
        super().__init__(message=message, status_code=404, code="SESSION_NOT_FOUND")


class MissingUserIdError(AppError):
    """缺少 X-User-Id 请求头。"""

    def __init__(self) -> None:
        super().__init__(
            message="缺少用户标识，请提供 X-User-Id 请求头",
            status_code=422,
            code="VALIDATION_ERROR",
        )
```

`register_exception_handlers` 已通过 `AppError` 基类处理，无需额外注册。

- [ ] **Step 2: 扩展 `COMMON_RESPONSES`**

在 `app/schemas/common.py`：

```python
COMMON_RESPONSES: dict[int, dict] = {
    404: {"model": ErrorResponse, "description": "资源不存在"},
    422: {"model": ErrorResponse, "description": "请求参数校验失败"},
    502: {"model": ErrorResponse, "description": "上游服务调用失败"},
}
```

- [ ] **Step 3: 在 `app/dependencies.py` 增加 `get_user_id`**

```python
from fastapi import Header

from app.core.exceptions import MissingUserIdError

USER_ID_HEADER = "X-User-Id"


def get_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id or not x_user_id.strip():
        raise MissingUserIdError()
    return x_user_id.strip()
```

- [ ] **Step 4: Commit**

```bash
git add app/core/exceptions.py app/dependencies.py app/schemas/common.py
git commit -m "feat: add SessionNotFoundError and X-User-Id dependency"
```

---

### Task 3: SessionStore 扩展（去 TTL + 用户索引，TDD）

**Files:**
- Modify: `app/services/session_store.py`
- Modify: `tests/test_session_store.py`
- Modify: `app/main.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: 替换 `tests/test_session_store.py` 为新版测试**

```python
from datetime import datetime, timezone

import pytest

from app.schemas.session import ChatMessage, SessionRecord
from app.services.session_store import InMemorySessionStore


def _record(session_id: str, user_id: str, *, updated_offset: float = 0) -> SessionRecord:
    now = datetime.now(timezone.utc)
    return SessionRecord(
        session_id=session_id,
        user_id=user_id,
        created_at=now,
        updated_at=now,
        messages=[ChatMessage(role="user", content="hi")],
    )


@pytest.mark.asyncio
async def test_create_and_get_roundtrip():
    store = InMemorySessionStore()
    record = _record("s1", "user-a")
    await store.create(record)
    loaded = await store.get("s1")
    assert loaded is not None
    assert loaded.user_id == "user-a"


@pytest.mark.asyncio
async def test_no_ttl_expiration():
    store = InMemorySessionStore()
    record = _record("s2", "user-a")
    await store.save(record)
    assert await store.get("s2") is not None


@pytest.mark.asyncio
async def test_list_by_user_sorted_by_updated_at_desc():
    store = InMemorySessionStore()
    r1 = _record("s1", "user-a")
    r2 = _record("s2", "user-a")
    await store.create(r1)
    await store.create(r2)
    r1.updated_at = datetime.now(timezone.utc)
    await store.save(r1)
    items, total = await store.list_by_user("user-a", offset=0, limit=10)
    assert total == 2
    assert items[0].session_id == "s1"


@pytest.mark.asyncio
async def test_list_by_user_isolated():
    store = InMemorySessionStore()
    await store.create(_record("s1", "user-a"))
    await store.create(_record("s2", "user-b"))
    items, total = await store.list_by_user("user-a", offset=0, limit=10)
    assert total == 1
    assert items[0].session_id == "s1"


@pytest.mark.asyncio
async def test_delete_removes_session_and_index():
    store = InMemorySessionStore()
    await store.create(_record("s1", "user-a"))
    assert await store.delete("s1") is True
    assert await store.get("s1") is None
    items, total = await store.list_by_user("user-a", offset=0, limit=10)
    assert total == 0
```

- [ ] **Step 2: 运行 FAIL**

Run: `uv run pytest tests/test_session_store.py -v`  
Expected: FAIL（`create` / `list_by_user` 不存在；`ttl_seconds` 签名不匹配）

- [ ] **Step 3: 重写 `app/services/session_store.py`**

要点：

```python
class SessionStore(ABC):
    @abstractmethod
    async def create(self, record: SessionRecord) -> None: ...
    @abstractmethod
    async def get(self, session_id: str) -> SessionRecord | None: ...
    @abstractmethod
    async def save(self, record: SessionRecord) -> None: ...
    @abstractmethod
    async def delete(self, session_id: str) -> bool: ...
    @abstractmethod
    async def list_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> tuple[list[SessionRecord], int]: ...


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._data: dict[str, SessionRecord] = {}
        self._user_index: dict[str, list[str]] = {}

    def _touch_index(self, record: SessionRecord) -> None:
        ids = self._user_index.setdefault(record.user_id, [])
        if record.session_id in ids:
            ids.remove(record.session_id)
        ids.insert(0, record.session_id)

    async def create(self, record: SessionRecord) -> None:
        self._data[record.session_id] = record
        self._touch_index(record)

    async def get(self, session_id: str) -> SessionRecord | None:
        return self._data.get(session_id)

    async def save(self, record: SessionRecord) -> None:
        self._data[record.session_id] = record
        self._touch_index(record)

    async def delete(self, session_id: str) -> bool:
        record = self._data.pop(session_id, None)
        if record is None:
            return False
        ids = self._user_index.get(record.user_id, [])
        if session_id in ids:
            ids.remove(session_id)
        return True

    async def list_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> tuple[list[SessionRecord], int]:
        ids = self._user_index.get(user_id, [])
        total = len(ids)
        slice_ids = ids[offset : offset + limit]
        records = [self._data[sid] for sid in slice_ids if sid in self._data]
        return records, total


class RedisSessionStore(SessionStore):
    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis
        self._client = redis.from_url(redis_url, decode_responses=True)

    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _user_key(self, user_id: str) -> str:
        return f"user:{user_id}:sessions"

    async def create(self, record: SessionRecord) -> None:
        await self.save(record)

    async def get(self, session_id: str) -> SessionRecord | None:
        raw = await self._client.get(self._session_key(session_id))
        if not raw:
            return None
        return SessionRecord.model_validate_json(raw)

    async def save(self, record: SessionRecord) -> None:
        ts = record.updated_at.timestamp()
        pipe = self._client.pipeline()
        pipe.set(self._session_key(record.session_id), record.model_dump_json())
        pipe.zadd(self._user_key(record.user_id), {record.session_id: ts})
        await pipe.execute()

    async def delete(self, session_id: str) -> bool:
        record = await self.get(session_id)
        if record is None:
            return False
        pipe = self._client.pipeline()
        pipe.delete(self._session_key(session_id))
        pipe.zrem(self._user_key(record.user_id), session_id)
        await pipe.execute()
        return True

    async def list_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> tuple[list[SessionRecord], int]:
        key = self._user_key(user_id)
        total = await self._client.zcard(key)
        ids = await self._client.zrevrange(key, offset, offset + limit - 1)
        records: list[SessionRecord] = []
        for sid in ids:
            rec = await self.get(sid)
            if rec:
                records.append(rec)
        return records, total


def build_session_store(store_type: str, redis_url: str) -> SessionStore:
    if store_type == "redis":
        return RedisSessionStore(redis_url=redis_url)
    return InMemorySessionStore()
```

- [ ] **Step 4: 更新 `app/main.py` 与 `tests/conftest.py`**

```python
# main.py lifespan
app.state.session_store = build_session_store(
    settings.session_store,
    settings.redis_url,
)

# conftest.py init_session_store
app.state.session_store = build_session_store(
    settings.session_store,
    settings.redis_url,
)
```

- [ ] **Step 5: 运行 PASS**

Run: `uv run pytest tests/test_session_store.py -v`  
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add app/services/session_store.py app/main.py tests/test_session_store.py tests/conftest.py
git commit -m "feat: extend session store with user index and no TTL"
```

---

### Task 4: SessionService（TDD）

**Files:**
- Create: `app/services/session_service.py`
- Create: `tests/test_session_service.py`

- [ ] **Step 1: 写失败测试**

```python
from datetime import datetime, timezone

import pytest

from app.core.exceptions import SessionNotFoundError
from app.schemas.session import ChatMessage, SessionRecord
from app.services.session_service import SessionService, make_preview
from app.services.session_store import InMemorySessionStore


def test_make_preview_truncates():
    assert make_preview("a" * 100).endswith("…")
    assert len(make_preview("short")) <= 80


@pytest.mark.asyncio
async def test_create_session_empty():
    store = InMemorySessionStore()
    svc = SessionService(store)
    detail = await svc.create_session("user-a")
    assert detail.session_id
    assert detail.messages == []
    assert detail.title == ""


@pytest.mark.asyncio
async def test_get_session_wrong_user_raises():
    store = InMemorySessionStore()
    svc = SessionService(store)
    detail = await svc.create_session("user-a")
    with pytest.raises(SessionNotFoundError):
        await svc.get_session("user-b", detail.session_id)


@pytest.mark.asyncio
async def test_list_sessions_maps_summary():
    store = InMemorySessionStore()
    svc = SessionService(store)
    await svc.create_session("user-a")
    data = await svc.list_sessions("user-a", page=1, page_size=20)
    assert data.total == 1
    assert data.items[0].message_count == 0


@pytest.mark.asyncio
async def test_delete_session():
    store = InMemorySessionStore()
    svc = SessionService(store)
    detail = await svc.create_session("user-a")
    assert await svc.delete_session("user-a", detail.session_id) is True
    with pytest.raises(SessionNotFoundError):
        await svc.get_session("user-a", detail.session_id)
```

- [ ] **Step 2: 运行 FAIL**

Run: `uv run pytest tests/test_session_service.py -v`

- [ ] **Step 3: 实现 `app/services/session_service.py`**

```python
import uuid
from datetime import datetime, timezone

from app.core.exceptions import SessionNotFoundError
from app.schemas.session import SessionRecord, SessionSummary
from app.schemas.sessions_api import SessionDetailData, SessionListData
from app.services.session_store import SessionStore

PREVIEW_MAX_LEN = 80


def make_preview(content: str) -> str:
    if len(content) <= PREVIEW_MAX_LEN:
        return content
    return content[: PREVIEW_MAX_LEN - 1] + "…"


class SessionService:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    async def _get_owned(self, user_id: str, session_id: str) -> SessionRecord:
        record = await self._store.get(session_id)
        if record is None or record.user_id != user_id:
            raise SessionNotFoundError()
        return record

    def _to_detail(self, record: SessionRecord) -> SessionDetailData:
        from app.schemas.sessions_api import SessionDetailData

        return SessionDetailData(
            session_id=record.session_id,
            title=record.title,
            created_at=record.created_at,
            updated_at=record.updated_at,
            messages=record.messages,
        )

    def _to_summary(self, record: SessionRecord) -> SessionSummary:
        preview = ""
        if record.messages:
            preview = make_preview(record.messages[-1].content)
        title = record.title or "新对话"
        return SessionSummary(
            session_id=record.session_id,
            title=title,
            created_at=record.created_at,
            updated_at=record.updated_at,
            preview=preview,
            message_count=len(record.messages),
        )

    async def create_session(self, user_id: str) -> SessionDetailData:
        now = datetime.now(timezone.utc)
        record = SessionRecord(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        await self._store.create(record)
        return self._to_detail(record)

    async def list_sessions(
        self, user_id: str, page: int, page_size: int
    ) -> SessionListData:
        offset = (page - 1) * page_size
        records, total = await self._store.list_by_user(user_id, offset, page_size)
        return SessionListData(
            items=[self._to_summary(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_session(self, user_id: str, session_id: str) -> SessionDetailData:
        record = await self._get_owned(user_id, session_id)
        return self._to_detail(record)

    async def delete_session(self, user_id: str, session_id: str) -> bool:
        await self._get_owned(user_id, session_id)
        return await self._store.delete(session_id)
```

- [ ] **Step 4: 运行 PASS**

Run: `uv run pytest tests/test_session_service.py -v`  
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/session_service.py tests/test_session_service.py
git commit -m "feat: add SessionService for session CRUD"
```

---

### Task 5: 标题生成 Prompt

**Files:**
- Modify: `app/llm/prompts.py`
- Create: `tests/test_session_title.py`

- [ ] **Step 1: 写失败测试**

```python
from app.llm.prompts import TITLE_SYSTEM_PROMPT, build_title_input, fallback_title


def test_build_title_input():
    text = build_title_input("COD怎么测", "采用 HJ 828-2017")
    assert "COD" in text


def test_fallback_title_truncates():
    assert len(fallback_title("a" * 100)) <= 30
```

- [ ] **Step 2: 在 `app/llm/prompts.py` 追加**

```python
TITLE_SYSTEM_PROMPT = (
    "你是会话标题助手。根据首轮问答生成一条简体中文标题，不超过20字，"
    "不要引号，不要句号，概括用户咨询主题。"
)


def build_title_input(user_msg: str, assistant_msg: str) -> str:
    return f"用户：{user_msg}\n助手：{assistant_msg}"


def fallback_title(first_user_message: str) -> str:
    text = first_user_message.strip()
    if len(text) <= 30:
        return text
    return text[:29] + "…"
```

- [ ] **Step 3: 运行 PASS 并 Commit**

Run: `uv run pytest tests/test_session_title.py -v`

```bash
git add app/llm/prompts.py tests/test_session_title.py
git commit -m "feat: add session title generation prompts"
```

---

### Task 6: ChatQueryService 改造（TDD）

**Files:**
- Modify: `app/services/chat_query_service.py`
- Modify: `tests/test_chat_query_service.py`

- [ ] **Step 1: 重写 `tests/test_chat_query_service.py`**

核心用例：

1. `test_query_requires_existing_session` — 无 session → `SessionNotFoundError`
2. `test_query_wrong_user` — 他人 session → `SessionNotFoundError`
3. `test_query_persists_sources_on_assistant_message`
4. `test_query_generates_title_after_first_turn` — summarizer 第二次响应为标题
5. `test_query_title_fallback_on_summarizer_failure` — summarizer 抛错时用截断
6. 保留 matched / not_matched 行为（需先 `create` 会话）

辅助 fixture：

```python
async def _create_session(store, user_id: str) -> str:
    from datetime import datetime, timezone
    import uuid
    from app.schemas.session import SessionRecord

    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await store.create(
        SessionRecord(session_id=sid, user_id=user_id, created_at=now, updated_at=now)
    )
    return sid
```

- [ ] **Step 2: 运行 FAIL**

Run: `uv run pytest tests/test_chat_query_service.py -v`

- [ ] **Step 3: 改造 `app/services/chat_query_service.py`**

关键变更：

```python
# 删除 SESSION_EXPIRED_WARNING 与 _resolve_session 懒创建逻辑

async def _load_session(self, session_id: str, user_id: str) -> SessionRecord:
    record = await self._store.get(session_id)
    if record is None or record.user_id != user_id:
        raise SessionNotFoundError()
    return record

async def _maybe_generate_title(
    self, record: SessionRecord, sources: list[SourceItem]
) -> None:
    if record.title or len(record.messages) != 2:
        return
    user_msg = record.messages[0].content
    assistant_msg = record.messages[1].content
    try:
        resp = await self._summarizer.ainvoke([
            SystemMessage(content=TITLE_SYSTEM_PROMPT),
            HumanMessage(content=build_title_input(user_msg, assistant_msg)),
        ])
        title = resp.content if isinstance(resp.content, str) else str(resp.content)
        record.title = title.strip()[:20]
    except Exception:
        logger.warning("title generation failed for session=%s", record.session_id)
        record.title = fallback_title(user_msg)

async def query(
    self,
    query: str,
    request_id: str | None,
    session_id: str,
    user_id: str,
) -> FactorQueryResponse:
    record = await self._load_session(session_id, user_id)
    await self._compressor.maybe_compress(record)
    # ... knowledge + llm 逻辑不变 ...
    sources = self._map_sources(payload)
    record.messages.append(ChatMessage(role="user", content=query))
    record.messages.append(
        ChatMessage(role="assistant", content=reply, sources=sources)
    )
    record.updated_at = datetime.now(timezone.utc)
    await self._maybe_generate_title(record, sources)
    await self._store.save(record)
    return FactorQueryResponse(..., data=FactorQueryData(..., warnings=[]))
```

构造函数增加 `self._summarizer` 引用（已有 summarizer 参数，用于 title）。

- [ ] **Step 4: 运行 PASS**

Run: `uv run pytest tests/test_chat_query_service.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/services/chat_query_service.py tests/test_chat_query_service.py
git commit -m "feat: require session ownership and persist sources in ChatQueryService"
```

---

### Task 7: Sessions API 路由

**Files:**
- Create: `app/api/v1/sessions.py`
- Modify: `app/api/v1/router.py`
- Modify: `app/dependencies.py`
- Create: `tests/test_sessions_api.py`

- [ ] **Step 1: 写失败集成测试 `tests/test_sessions_api.py`**

```python
import pytest

USER_HEADER = {"X-User-Id": "test-user"}


@pytest.mark.asyncio
async def test_create_session(client):
    resp = await client.post("/api/v1/sessions", headers=USER_HEADER)
    assert resp.status_code == 200
    assert resp.json()["data"]["session_id"]


@pytest.mark.asyncio
async def test_missing_user_id_returns_422(client):
    resp = await client.post("/api/v1/sessions")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_and_get_session(client):
    created = await client.post("/api/v1/sessions", headers=USER_HEADER)
    session_id = created.json()["data"]["session_id"]
    listed = await client.get("/api/v1/sessions", headers=USER_HEADER)
    assert listed.json()["data"]["total"] >= 1
    detail = await client.get(f"/api/v1/sessions/{session_id}", headers=USER_HEADER)
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_delete_session(client):
    created = await client.post("/api/v1/sessions", headers=USER_HEADER)
    session_id = created.json()["data"]["session_id"]
    deleted = await client.delete(f"/api/v1/sessions/{session_id}", headers=USER_HEADER)
    assert deleted.json()["data"]["deleted"] is True
    detail = await client.get(f"/api/v1/sessions/{session_id}", headers=USER_HEADER)
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_get_other_user_session_404(client):
    created = await client.post("/api/v1/sessions", headers={"X-User-Id": "owner"})
    session_id = created.json()["data"]["session_id"]
    resp = await client.get(
        f"/api/v1/sessions/{session_id}",
        headers={"X-User-Id": "other"},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: 创建 `app/api/v1/sessions.py`**

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request

from app.dependencies import get_session_service_dep, get_user_id
from app.schemas.common import COMMON_RESPONSES
from app.schemas.sessions_api import (
    SessionDeleteResponse,
    SessionDetailResponse,
    SessionListResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions")


@router.post("", response_model=SessionDetailResponse, responses=COMMON_RESPONSES)
async def create_session(
    request: Request,
    user_id: str = Depends(get_user_id),
    session_service: SessionService = Depends(get_session_service_dep),
):
    detail = await session_service.create_session(user_id)
    return SessionDetailResponse(
        success=True,
        code="OK",
        message="创建成功",
        request_id=getattr(request.state, "request_id", None),
        data=detail,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("", response_model=SessionListResponse, responses=COMMON_RESPONSES)
async def list_sessions(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_user_id),
    session_service: SessionService = Depends(get_session_service_dep),
):
    data = await session_service.list_sessions(user_id, page, page_size)
    return SessionListResponse(
        success=True,
        code="OK",
        message="查询成功",
        request_id=getattr(request.state, "request_id", None),
        data=data,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/{session_id}", response_model=SessionDetailResponse, responses=COMMON_RESPONSES)
async def get_session(
    session_id: str,
    request: Request,
    user_id: str = Depends(get_user_id),
    session_service: SessionService = Depends(get_session_service_dep),
):
    detail = await session_service.get_session(user_id, session_id)
    return SessionDetailResponse(
        success=True,
        code="OK",
        message="查询成功",
        request_id=getattr(request.state, "request_id", None),
        data=detail,
        timestamp=datetime.now(timezone.utc),
    )


@router.delete("/{session_id}", response_model=SessionDeleteResponse, responses=COMMON_RESPONSES)
async def delete_session(
    session_id: str,
    request: Request,
    user_id: str = Depends(get_user_id),
    session_service: SessionService = Depends(get_session_service_dep),
):
    from app.schemas.sessions_api import SessionDeleteData

    await session_service.delete_session(user_id, session_id)
    return SessionDeleteResponse(
        success=True,
        code="OK",
        message="删除成功",
        request_id=getattr(request.state, "request_id", None),
        data=SessionDeleteData(deleted=True),
        timestamp=datetime.now(timezone.utc),
    )
```

- [ ] **Step 3: 在 `dependencies.py` 增加**

```python
from app.services.session_service import SessionService

def get_session_service(session_store: SessionStore) -> SessionService:
    return SessionService(session_store)

def get_session_service_dep(request: Request) -> SessionService:
    return get_session_service(request.app.state.session_store)
```

- [ ] **Step 4: 注册路由 `app/api/v1/router.py`**

```python
from app.api.v1 import factors, health, sessions

v1_router.include_router(sessions.router, tags=["sessions"])
```

- [ ] **Step 5: 运行 PASS**

Run: `uv run pytest tests/test_sessions_api.py -v`  
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add app/api/v1/sessions.py app/api/v1/router.py app/dependencies.py tests/test_sessions_api.py
git commit -m "feat: add sessions CRUD API endpoints"
```

---

### Task 8: 改造 factors/query 路由

**Files:**
- Modify: `app/api/v1/factors.py`
- Modify: `app/dependencies.py`
- Modify: `tests/test_factors.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: 修改 `factors.py`**

```python
from app.dependencies import get_chat_query_service_dep, get_factor_service_dep, get_user_id

async def query_factor(
    body: FactorQueryRequest,
    request: Request,
    user_id: str = Depends(get_user_id),
    chat_service: ChatQueryService = Depends(get_chat_query_service_dep),
):
    request_id = getattr(request.state, "request_id", None)
    return await chat_service.query(
        query=body.query,
        request_id=request_id,
        session_id=body.session_id,
        user_id=user_id,
    )
```

- [ ] **Step 2: 更新 `tests/conftest.py` 增加 header 常量**

```python
DEFAULT_USER_HEADERS = {"X-User-Id": "test-user"}
```

- [ ] **Step 3: 更新 `tests/test_factors.py`**

所有 `client.post("/api/v1/factors/query", ...)` 增加：

```python
headers={"X-User-Id": "test-user"},
json={"query": "...", "session_id": "existing-session-id"},
```

新增用例：

- `test_factor_query_missing_user_id_422`
- `test_factor_query_blank_query_422` — `{"query": "   ", "session_id": "s1"}`
- `test_factor_query_missing_session_id_422`

未 mock 的端到端测试：先 `POST /sessions` 取 `session_id`，再 query（可选，若仍 mock service 则只测 header 校验）。

- [ ] **Step 4: 全量测试**

Run: `uv run pytest -v`  
Expected: 全部 passed（修复 `test_context_compressor` 若 `ChatMessage` 签名变化无影响）

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/factors.py app/dependencies.py tests/test_factors.py tests/conftest.py
git commit -m "feat: require X-User-Id and session_id on factor query"
```

---

### Task 9: 文档与配置说明

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/superpowers/specs/2026-06-03-multi-turn-session-design.md`（状态改为「已评审」）

- [ ] **Step 1: README 增加**

- 会话 API 四端点说明
- `X-User-Id` 必填
- 典型联调流程（create → query → list → get → delete）
- 破坏性变更：`session_id` 必填、无懒创建
- `SESSION_TTL_SECONDS` 已废弃说明

- [ ] **Step 2: `.env.example` 注释 `SESSION_TTL_SECONDS` 为 ignored**

- [ ] **Step 3: Commit**

```bash
git add README.md .env.example docs/superpowers/specs/2026-06-03-multi-turn-session-design.md
git commit -m "docs: document multi-turn session API and breaking changes"
```

---

## Spec Coverage Checklist

| Spec 要求 | Task |
|-----------|------|
| `X-User-Id` 归属 | Task 2, 7, 8 |
| 无 TTL / DELETE 清理 | Task 3 |
| `POST/GET/GET{id}/DELETE /sessions` | Task 4, 7 |
| `session_id` 必填、取消懒创建 | Task 1, 6, 8 |
| assistant `sources` 落库 | Task 1, 6 |
| 首轮 LLM 标题 + 回退 | Task 5, 6 |
| 空/空白 query 422 | Task 1, 8 |
| 越权统一 404 | Task 2, 4, 6, 7 |
| Memory/Redis 用户索引 | Task 3 |
| ContextCompressor 不变 | Task 6（仅调用，不改逻辑） |
| 测试 | Task 1–8 |
| README / 破坏性变更 | Task 9 |

---

## 验证命令（完成全部 Task 后）

```bash
cd D:\project_all\enviro-nexus-api
uv run pytest -v
```

手动冒烟：

```bash
uv run uvicorn app.main:app --port 8080

# 1. 创建会话
curl -X POST http://localhost:8080/api/v1/sessions -H "X-User-Id: demo-user"

# 2. 发消息（替换 SESSION_ID）
curl -X POST http://localhost:8080/api/v1/factors/query \
  -H "Content-Type: application/json" \
  -H "X-User-Id: demo-user" \
  -d "{\"query\":\"COD怎么测？\",\"session_id\":\"SESSION_ID\"}"

# 3. 历史列表
curl http://localhost:8080/api/v1/sessions -H "X-User-Id: demo-user"
```

---

## 给前端团队的破坏性变更摘要

1. 所有请求加 `X-User-Id`。
2. 「新对话」先调 `POST /api/v1/sessions`，再带返回的 `session_id` 调 query。
3. `session_id` 必填；过期/无效 id 返回 404，不再自动开新会话。
4. 历史侧边栏调 `GET /api/v1/sessions`；打开会话调 `GET /api/v1/sessions/{id}`（messages 含 sources）。
5. 删除调 `DELETE /api/v1/sessions/{id}`。
