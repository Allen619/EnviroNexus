# Factor Name Knowledge Pass-Through Implementation Plan

> Superseded on 2026-06-05: enviro-nexus-knowledge accepts only `{ "query": ... }` for `POST /api/v1/factors/query`; API keeps `factor_name` only as a legacy ignored field and does not validate or pass it through.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add required `factor_name` input to factor query requests and pass it through to the knowledge service for both streaming and non-streaming query paths.

**Architecture:** Keep the current shared request model and shared `ChatQueryService._prepare_turn()` flow. `query` remains the user message and LLM prompt input; `factor_name` is validated by API, passed through service methods, and sent by `KnowledgeClient` as an additional knowledge request field.

**Tech Stack:** FastAPI, Pydantic v2, httpx, LangChain fake chat models, pytest-asyncio, uv

**Spec:** `docs/superpowers/specs/2026-06-04-factor-name-knowledge-pass-through-design.md`

---

## File Map

| Action | Path | Responsibility |
| --- | --- | --- |
| Modify | `app/schemas/chat_query.py` | Add and validate `FactorQueryRequest.factor_name` |
| Modify | `app/api/v1/factors.py` | Pass `body.factor_name` to sync and stream service methods |
| Modify | `app/services/chat_query_service.py` | Thread `factor_name` through `query`, `query_stream`, and `_prepare_turn` |
| Modify | `app/clients/knowledge_client.py` | Send `factor_name` to knowledge `/api/v1/factors/query` |
| Modify | `tests/test_factors.py` | Cover API validation and sync request pass-through behavior |
| Modify | `tests/test_factors_stream.py` | Cover stream API validation and route pass-through behavior |
| Modify | `tests/test_chat_query_service.py` | Cover service sync pass-through to knowledge client |
| Modify | `tests/test_chat_query_stream.py` | Cover service stream pass-through to knowledge client |
| Create | `tests/test_knowledge_client.py` | Cover knowledge request JSON payload |
| Modify | `README.md` | Update curl examples with `factor_name` |

---

## Task 1: Request Schema Validation

**Files:**
- Modify: `tests/test_factors.py`
- Modify: `tests/test_factors_stream.py`
- Modify: `app/schemas/chat_query.py`

- [ ] **Step 1: Write failing API validation tests**

Add these tests to `tests/test_factors.py`:

```python
@pytest.mark.asyncio
async def test_factor_query_missing_factor_name_422(client):
    response = await client.post(
        "/api/v1/factors/query",
        headers=USER_HEADERS,
        json={"query": "COD", "session_id": "test-session-id"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_factor_query_blank_factor_name_422(client):
    response = await client.post(
        "/api/v1/factors/query",
        headers=USER_HEADERS,
        json={"query": "COD", "session_id": "test-session-id", "factor_name": "   "},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
```

Add this test to `tests/test_factors_stream.py`:

```python
@pytest.mark.asyncio
async def test_factor_query_stream_missing_factor_name_422(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        headers=DEFAULT_USER_HEADERS,
        json={"query": "COD", "session_id": "stream-session-1"},
    )

    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_factor_query_stream_blank_factor_name_422(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        headers=DEFAULT_USER_HEADERS,
        json={"query": "COD", "session_id": "stream-session-1", "factor_name": "   "},
    )

    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "VALIDATION_ERROR"
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
uv run pytest tests/test_factors.py::test_factor_query_missing_factor_name_422 tests/test_factors.py::test_factor_query_blank_factor_name_422 tests/test_factors_stream.py::test_factor_query_stream_missing_factor_name_422 tests/test_factors_stream.py::test_factor_query_stream_blank_factor_name_422 -v
```

Expected: missing-field tests fail with HTTP 200 or stream output, blank-field tests fail with HTTP 200 because `factor_name` is not validated yet.

- [ ] **Step 3: Implement request field**

Update `FactorQueryRequest` in `app/schemas/chat_query.py`:

```python
class FactorQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="用户问题，首尾空白会被 trim")
    session_id: str = Field(..., min_length=1, description="会话 ID，须先 POST /api/v1/sessions 创建")
    factor_name: str = Field(..., min_length=1, description="因子名，由前端输入并透传给 knowledge 服务")

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("请输入问题内容")
        return stripped

    @field_validator("factor_name")
    @classmethod
    def strip_factor_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("请输入因子名")
        return stripped
```

- [ ] **Step 4: Run tests to verify GREEN**

Run the same command from Step 2.

Expected: all four tests pass.

---

## Task 2: Route and Service Pass-Through

**Files:**
- Modify: `tests/test_factors.py`
- Modify: `tests/test_factors_stream.py`
- Modify: `tests/test_chat_query_service.py`
- Modify: `tests/test_chat_query_stream.py`
- Modify: `app/api/v1/factors.py`
- Modify: `app/services/chat_query_service.py`

- [ ] **Step 1: Write failing pass-through tests**

Update shared request bodies in API tests so valid calls include `factor_name`:

```python
DEFAULT_QUERY_BODY = {
    "query": "COD 怎么测？",
    "session_id": "test-session-id",
    "factor_name": "化学需氧量",
}
```

```python
STREAM_BODY = {
    "query": "COD 怎么测？",
    "session_id": "stream-session-1",
    "factor_name": "化学需氧量",
}
```

Add route assertions:

```python
assert patched_query.call_args.kwargs["factor_name"] == "化学需氧量"
```

Add service assertions:

```python
knowledge.query_factor.assert_awaited_once_with("COD怎么测", "化学需氧量")
```

For stream service tests, collect the stream first, then assert:

```python
knowledge.query_factor.assert_awaited_once_with("COD", "化学需氧量")
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
uv run pytest tests/test_factors.py tests/test_factors_stream.py tests/test_chat_query_service.py tests/test_chat_query_stream.py -v
```

Expected: tests fail because route and service method signatures do not accept `factor_name`.

- [ ] **Step 3: Implement route and service threading**

Update `app/api/v1/factors.py` service calls:

```python
return await chat_service.query(
    query=body.query,
    factor_name=body.factor_name,
    request_id=request_id,
    session_id=body.session_id,
    user_id=user_id,
)
```

```python
chat_service.query_stream(
    query=body.query,
    factor_name=body.factor_name,
    session_id=body.session_id,
    user_id=user_id,
)
```

Update `ChatQueryService` signatures and `_prepare_turn` call:

```python
async def _prepare_turn(self, query: str, factor_name: str, session_id: str, user_id: str) -> TurnContext:
    ...
    payload = await self._knowledge.query_factor(query, factor_name)
```

```python
async def query(self, query: str, factor_name: str, request_id: str | None, session_id: str, user_id: str) -> FactorQueryResponse:
    ctx = await self._prepare_turn(query, factor_name, session_id, user_id)
```

```python
async def query_stream(self, query: str, factor_name: str, session_id: str, user_id: str):
    ctx = await self._prepare_turn(query, factor_name, session_id, user_id)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run the command from Step 2.

Expected: route and service tests pass except knowledge-client-specific tests not yet added.

---

## Task 3: Knowledge Client Payload

**Files:**
- Create: `tests/test_knowledge_client.py`
- Modify: `app/clients/knowledge_client.py`

- [ ] **Step 1: Write failing client test**

Create `tests/test_knowledge_client.py`:

```python
import pytest

from app.clients.knowledge_client import KnowledgeClient
from app.config.settings import Settings


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"matched": False, "warnings": []}


class CapturingHttpClient:
    def __init__(self):
        self.calls = []

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse()


@pytest.mark.asyncio
async def test_query_factor_sends_factor_name_to_knowledge():
    http_client = CapturingHttpClient()
    settings = Settings(knowledge_service_base_url="http://knowledge.test")
    client = KnowledgeClient(http_client=http_client, settings=settings)

    await client.query_factor("COD 怎么测？", "化学需氧量")

    method, url, kwargs = http_client.calls[0]
    assert method == "POST"
    assert url == "http://knowledge.test/api/v1/factors/query"
    assert kwargs["json"] == {"query": "COD 怎么测？", "factor_name": "化学需氧量"}
```

- [ ] **Step 2: Run test to verify RED**

Run:

```powershell
uv run pytest tests/test_knowledge_client.py -v
```

Expected: fail because `KnowledgeClient.query_factor()` accepts only `query`.

- [ ] **Step 3: Implement client payload**

Update `app/clients/knowledge_client.py`:

```python
async def query_factor(self, query: str, factor_name: str) -> KnowledgeFactorQueryPayload:
    """调用知识服务的因子查询接口。"""
    url = f"{self._base_url}/api/v1/factors/query"
    data = await self._request(
        "POST",
        url,
        json={"query": query, "factor_name": factor_name},
    )
    return self._validate_payload(KnowledgeFactorQueryPayload, data, url)
```

- [ ] **Step 4: Run test to verify GREEN**

Run:

```powershell
uv run pytest tests/test_knowledge_client.py -v
```

Expected: pass.

---

## Task 4: Documentation and Regression

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-06-03-stream-query-design.md`

- [ ] **Step 1: Update docs examples**

Update README curl examples to include:

```json
{"session_id":"<session_id>","query":"COD 怎么测？","factor_name":"化学需氧量"}
```

Add a note to the old stream-query design that the latest request body now includes required `factor_name` per `2026-06-04-factor-name-knowledge-pass-through-design.md`.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
uv run pytest tests/test_knowledge_client.py tests/test_chat_query_service.py tests/test_chat_query_stream.py tests/test_factors.py tests/test_factors_stream.py -v
```

Expected: all selected tests pass.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit changed files**

Run:

```powershell
git add app/clients/knowledge_client.py app/schemas/chat_query.py app/api/v1/factors.py app/services/chat_query_service.py tests/test_knowledge_client.py tests/test_chat_query_service.py tests/test_chat_query_stream.py tests/test_factors.py tests/test_factors_stream.py README.md docs/superpowers/specs/2026-06-03-stream-query-design.md docs/superpowers/specs/2026-06-04-factor-name-knowledge-pass-through-design.md docs/superpowers/plans/2026-06-04-factor-name-knowledge-pass-through.md
git commit -m "feat: pass factor name to knowledge service"
```
