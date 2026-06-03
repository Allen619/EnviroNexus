# Day 1.6 Knowledge API Contract & Public MethodCard API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task after user approval. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the `enviro-nexus-knowledge` HTTP API contract for backend/frontend callers by adding public MethodCard list and detail endpoints while preserving the existing factor query behavior.

**Architecture:** Keep Day 1.5's deterministic chain intact: seed MethodCard JSON is imported into PostgreSQL, repository functions read approved + enabled cards, service functions shape public response DTOs, and FastAPI routes expose versioned `/api/v1` endpoints. Add a public MethodCard serialization boundary so governance, change log, extensions, source file metadata, and internal extraction details never leak to frontend-facing APIs.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL 16, pytest, httpx ASGITransport, existing Day 1.5 seed/import/query stack.

---

## 1. Scope

This is Day 1.6 only.

Allowed:

- Modify files only under `enviro-nexus-knowledge`.
- Add public MethodCard list/detail APIs under `/api/v1`.
- Keep `POST /api/v1/factors/query` response compatible.
- Add repository functions to list and fetch approved + enabled MethodCards.
- Add public response schema / builder functions for frontend-safe MethodCard payloads.
- Add integration tests against the existing real PostgreSQL test setup.
- Add or update `enviro-nexus-knowledge/docs/api-contract.md`.

Not allowed:

- Do not modify `enviro-nexus-api`.
- Do not modify `enviro-nexus-web`.
- Do not change Day 1.5 seed semantics.
- Do not introduce RAG.
- Do not introduce embeddings.
- Do not introduce pgvector.
- Do not introduce LLM answering.
- Do not parse PDF.
- Do not add PDF/markdown extraction pipelines.
- Do not break `POST /api/v1/factors/query` tests or response structure.

## 2. Current Baseline

Already available:

```text
GET /api/v1/health
POST /api/v1/factors/query
```

Current data:

```text
method_cards: 5
factor_aliases: 21
source_documents: 5
```

Existing implementation patterns:

```text
app/main.py
  includes route modules under /api/v1

app/api/routes/factor_query.py
  owns POST /factors/query HTTP concerns and error translation

app/services/query_service.py
  orchestrates query normalize -> alias match -> card load -> answer build

app/db/repositories.py
  owns SQLAlchemy persistence/query functions

app/core/answer_builder.py
app/core/evidence_builder.py
  shape public answer payload for factor query
```

Day 1.6 should follow the same route -> service -> repository -> builder shape.

## 3. Target API Contract

### 3.1 Existing Endpoint: Factor Query

Endpoint:

```text
POST /api/v1/factors/query
```

Request:

```json
{
  "query": "CODMn 怎么测？"
}
```

Compatibility requirement:

- Keep existing response keys unchanged:

```text
api_version
matched
factor
matched_alias
match_confidence
card_id
answer
warnings
```

- Keep `COD 怎么测？` unmatched.
- Keep `CODMn 怎么测？` matched to `water_permanganate_index_hj1445_2026`.
- Keep `answer.evidence_refs` non-empty for matched cards.
- Do not expose governance fields in `answer`.

### 3.2 New Endpoint: Public MethodCard List

Endpoint:

```text
GET /api/v1/method-cards
```

Purpose:

Return frontend-safe summaries for all MethodCards where:

```text
review_status = approved
answer_visibility = enabled
```

Response status:

```text
200 OK
```

Response shape:

```json
{
  "api_version": "v1",
  "items": [
    {
      "card_id": "water_ph_hj1147_2020",
      "factor": "pH 值",
      "category": "水质",
      "standard_code": "HJ 1147-2020",
      "standard_name": "水质 pH 值的测定 电极法",
      "method_name": "电极法",
      "applicability": "适用于地表水、地下水、生活污水和工业废水中 pH 值的测定，测定范围为 0～14。"
    }
  ],
  "count": 5
}
```

List item contract:

- Must include `card_id`, `factor`, `category`, `standard_code`, `standard_name`, `method_name`, `applicability`.
- Must not include `governance`, `change_log`, `extensions`, `source_document`, `file_path`, `metadata`, `checksum_sha256`, `evidence_ids`.
- Order should be stable:

```text
category ASC, factor ASC, standard_code ASC, card_id ASC
```

Stable ordering makes frontend rendering and tests deterministic.

### 3.3 New Endpoint: Public MethodCard Detail

Endpoint:

```text
GET /api/v1/method-cards/{card_id}/public
```

Purpose:

Return one frontend-safe MethodCard detail, only if approved + enabled.

Response status:

```text
200 OK
```

Response shape:

```json
{
  "api_version": "v1",
  "card": {
    "card_id": "water_ph_hj1147_2020",
    "factor": "pH 值",
    "category": "水质",
    "standard_code": "HJ 1147-2020",
    "standard_name": "水质 pH 值的测定 电极法",
    "method_name": "电极法",
    "applicability": "适用于地表水、地下水、生活污水和工业废水中 pH 值的测定，测定范围为 0～14。",
    "measurement": {
      "principle": "pH 值由参比电极和氢离子指示电极组成的测量电池电动势而得，仪器直接以 pH 读数表示。",
      "instrument": "酸度计、分体式 pH 电极或复合 pH 电极、温度计、采样瓶和烧杯",
      "unit": null,
      "range": {
        "lower": "0",
        "upper": "14",
        "unit": "pH"
      }
    },
    "requirements": [
      {
        "type": "sample_collection",
        "title": "样品采集与保存",
        "content": "按照相关监测规范采集样品，可现场测定；实验室测定时样品应充满采样瓶并立即密封，2 h 内完成测定。"
      }
    ],
    "qa_qc": [
      {
        "title": "校准与质控",
        "content": "每批样品测定前应校准仪器；每 20 个样品或每批次应分析有证标准样品或标准物质，并分析平行样。"
      }
    ],
    "evidence_refs": [
      {
        "source_title": "HJ 1147-2020",
        "section": "1 适用范围",
        "page": 1,
        "summary": "标准规定了测定水中 pH 值的电极法，适用于地表水、地下水、生活污水和工业废水，测定范围为 0～14。"
      }
    ]
  }
}
```

Public detail contract:

- Must include:

```text
card_id
factor
category
standard_code
standard_name
method_name
applicability
measurement
requirements
qa_qc
evidence_refs
```

- `evidence_refs` must only include:

```text
source_title
section
page
summary
```

- Must not include:

```text
governance
change_log
extensions
source_document
source_doc_id
file_path
metadata
checksum_sha256
evidence_id
evidence_ids
manual_extract_source
needs_pdf_check
```

### 3.4 Optional Internal Debug Endpoint

Endpoint:

```text
GET /api/v1/method-cards/{card_id}
```

Decision:

- There is currently no debug endpoint.
- Day 1.6 may add it only if useful for local inspection.
- If added, it must be documented as **internal debug only** and **not a long-term frontend contract**.
- The public frontend contract remains:

```text
GET /api/v1/method-cards
GET /api/v1/method-cards/{card_id}/public
```

Recommended implementation:

- Skip the internal debug endpoint unless it materially helps testing.
- Avoid expanding the public surface unnecessarily.

## 4. Error Contract

### 4.1 Not Found

When a public card detail is requested with a missing, draft, rejected, or disabled card:

```text
GET /api/v1/method-cards/not_exists/public
```

Return:

```text
404 Not Found
```

Body:

```json
{
  "error_code": "method_card_not_found",
  "message": "method card is not found or not public",
  "api_version": "v1"
}
```

### 4.2 Database Unavailable

If SQLAlchemy raises a database error:

```text
503 Service Unavailable
```

Body:

```json
{
  "error_code": "database_unavailable",
  "message": "database is unavailable",
  "api_version": "v1"
}
```

### 4.3 Validation Errors

FastAPI default validation behavior is acceptable:

```text
422 Unprocessable Entity
```

Do not override it unless a test requires a stable application error.

## 5. File Structure

### 5.1 New Files

```text
enviro-nexus-knowledge/app/api/routes/method_cards.py
enviro-nexus-knowledge/app/services/method_card_service.py
enviro-nexus-knowledge/app/core/public_method_card_builder.py
enviro-nexus-knowledge/tests/integration/test_method_cards_api.py
enviro-nexus-knowledge/docs/api-contract.md
```

Responsibilities:

- `method_cards.py`: HTTP route definitions and HTTP error translation.
- `method_card_service.py`: session-level orchestration for listing and fetching public cards.
- `public_method_card_builder.py`: frontend-safe MethodCard serialization boundary.
- `test_method_cards_api.py`: integration tests for public list/detail/404/visibility.
- `api-contract.md`: human-readable API contract for backend/frontend use.

### 5.2 Modified Files

```text
enviro-nexus-knowledge/app/main.py
enviro-nexus-knowledge/app/db/repositories.py
enviro-nexus-knowledge/app/schemas/response.py
```

Responsibilities:

- `main.py`: register `method_cards_router` under `/api/v1`.
- `repositories.py`: add approved+enabled list/detail query functions and test helper update if needed.
- `response.py`: add Pydantic response models for public MethodCard list/detail and shared error response.

### 5.3 Files That Must Not Change

```text
enviro-nexus-api/
enviro-nexus-web/
```

## 6. Implementation Tasks

### Task 1: Baseline and Guardrails

**Files:** no writes.

- [ ] Check current status:

```powershell
cd D:\szy\code\my-project\enviro-nexus
git -c core.quotepath=false status --short
git -c core.quotepath=false status --short -- enviro-nexus-api enviro-nexus-web
```

Expected:

```text
enviro-nexus-api and enviro-nexus-web status output is empty
```

- [ ] Ensure local database is running:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
docker compose up -d postgres
uv run alembic upgrade head
uv run python -m app.services.import_service --seed data/seed --mode upsert
```

- [ ] Run existing tests before changes:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run pytest -v
```

Expected:

```text
35 passed
```

If baseline fails, stop and report before implementing.

### Task 2: Public Builder Tests First

**Files:**

- Create: `enviro-nexus-knowledge/app/core/public_method_card_builder.py`
- Modify: `enviro-nexus-knowledge/tests/unit/test_answer_builder.py`

Add tests to existing unit coverage or create a new unit test file if cleaner:

```text
enviro-nexus-knowledge/tests/unit/test_public_method_card_builder.py
```

Recommended new unit test file:

```python
import json
from pathlib import Path

from app.core.public_method_card_builder import (
    build_public_method_card_detail,
    build_public_method_card_summary,
)
from app.schemas.method_card import MethodCard


def load_card(card_id: str) -> MethodCard:
    path = Path("data/seed/method_cards") / f"{card_id}.json"
    return MethodCard.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_build_public_method_card_summary_omits_governance_and_internal_fields():
    card = load_card("water_ph_hj1147_2020")

    summary = build_public_method_card_summary(card)
    serialized = json.dumps(summary, ensure_ascii=False)

    assert summary == {
        "card_id": "water_ph_hj1147_2020",
        "factor": "pH 值",
        "category": "水质",
        "standard_code": "HJ 1147-2020",
        "standard_name": "水质 pH 值的测定 电极法",
        "method_name": "电极法",
        "applicability": card.applicability.scope_summary,
    }
    assert "governance" not in serialized
    assert "change_log" not in serialized
    assert "extensions" not in serialized
    assert "file_path" not in serialized
    assert "evidence_id" not in serialized
    assert "evidence_ids" not in serialized


def test_build_public_method_card_detail_returns_frontend_safe_fields():
    card = load_card("water_ph_hj1147_2020")

    detail = build_public_method_card_detail(card)
    serialized = json.dumps(detail, ensure_ascii=False)

    assert detail["card_id"] == "water_ph_hj1147_2020"
    assert detail["factor"] == "pH 值"
    assert detail["category"] == "水质"
    assert detail["standard_code"] == "HJ 1147-2020"
    assert detail["standard_name"] == "水质 pH 值的测定 电极法"
    assert detail["method_name"] == "电极法"
    assert detail["applicability"]
    assert detail["measurement"]
    assert detail["requirements"]
    assert detail["qa_qc"]
    assert detail["evidence_refs"]
    assert set(detail["evidence_refs"][0].keys()) == {
        "source_title",
        "section",
        "page",
        "summary",
    }
    assert "governance" not in serialized
    assert "change_log" not in serialized
    assert "extensions" not in serialized
    assert "source_document" not in serialized
    assert "file_path" not in serialized
    assert "metadata" not in serialized
    assert "manual_extract_source" not in serialized
    assert "needs_pdf_check" not in serialized
    assert "evidence_id" not in serialized
    assert "evidence_ids" not in serialized
```

- [ ] Run the new unit test before implementation:

```powershell
uv run pytest tests/unit/test_public_method_card_builder.py -v
```

Expected RED:

```text
ModuleNotFoundError: No module named 'app.core.public_method_card_builder'
```

- [ ] Implement `public_method_card_builder.py` with:

```python
from app.schemas.method_card import MethodCard


def build_public_method_card_summary(card: MethodCard) -> dict:
    return {
        "card_id": card.card_id,
        "factor": card.identity.factor,
        "category": card.identity.category,
        "standard_code": card.identity.standard_code,
        "standard_name": card.identity.standard_name,
        "method_name": card.identity.method_name,
        "applicability": card.applicability.scope_summary,
    }


def build_public_method_card_detail(card: MethodCard) -> dict:
    measurement_range = card.measurement.range
    return {
        "card_id": card.card_id,
        "factor": card.identity.factor,
        "category": card.identity.category,
        "standard_code": card.identity.standard_code,
        "standard_name": card.identity.standard_name,
        "method_name": card.identity.method_name,
        "applicability": card.applicability.scope_summary,
        "measurement": {
            "principle": card.measurement.principle,
            "instrument": card.measurement.instrument,
            "unit": card.measurement.unit,
            "range": None
            if measurement_range is None
            else {
                "lower": measurement_range.lower,
                "upper": measurement_range.upper,
                "unit": measurement_range.unit,
            },
        },
        "requirements": [
            {
                "type": requirement.type,
                "title": requirement.title,
                "content": requirement.content,
            }
            for requirement in card.requirements
        ],
        "qa_qc": [
            {
                "title": item.title,
                "content": item.content,
            }
            for item in card.qa_qc
        ],
        "evidence_refs": [
            {
                "source_title": evidence.source_title,
                "section": evidence.section,
                "page": evidence.page,
                "summary": evidence.summary,
            }
            for evidence in card.evidence_refs
        ],
    }
```

- [ ] Run unit test again:

```powershell
uv run pytest tests/unit/test_public_method_card_builder.py -v
```

Expected GREEN:

```text
passed
```

### Task 3: Repository Functions

**Files:**

- Modify: `enviro-nexus-knowledge/app/db/repositories.py`

Add repository functions:

```python
def list_public_method_card_jsons(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(MethodCardRow.card_json)
        .where(MethodCardRow.review_status == "approved")
        .where(MethodCardRow.answer_visibility == "enabled")
        .order_by(
            MethodCardRow.category.asc(),
            MethodCardRow.factor.asc(),
            MethodCardRow.standard_code.asc(),
            MethodCardRow.card_id.asc(),
        )
    ).all()
    return [row.card_json for row in rows]


def get_public_method_card_json(session: Session, card_id: str) -> dict[str, Any] | None:
    return session.execute(
        select(MethodCardRow.card_json)
        .where(MethodCardRow.card_id == card_id)
        .where(MethodCardRow.review_status == "approved")
        .where(MethodCardRow.answer_visibility == "enabled")
    ).scalar_one_or_none()


def get_method_card_json(session: Session, card_id: str) -> dict[str, Any] | None:
    return session.execute(
        select(MethodCardRow.card_json)
        .where(MethodCardRow.card_id == card_id)
    ).scalar_one_or_none()
```

Notes:

- `get_public_method_card_json` is the public contract path.
- `get_method_card_json` is only needed if implementing optional internal debug endpoint.
- Do not remove `get_enabled_method_card_json` because `query_service.py` already uses it.

Verification:

```powershell
uv run pytest tests/unit -v
```

Expected:

```text
all unit tests pass
```

### Task 4: Response Models

**Files:**

- Modify: `enviro-nexus-knowledge/app/schemas/response.py`

Add Pydantic models:

```python
class PublicMeasurementRange(BaseModel):
    lower: str | None = None
    upper: str | None = None
    unit: str | None = None


class PublicMeasurement(BaseModel):
    principle: str
    instrument: str
    unit: str | None = None
    range: PublicMeasurementRange | None = None


class PublicRequirement(BaseModel):
    type: str
    title: str
    content: str


class PublicQaQcItem(BaseModel):
    title: str
    content: str


class PublicEvidenceRef(BaseModel):
    source_title: str
    section: str
    page: int | None = None
    summary: str


class PublicMethodCardSummary(BaseModel):
    card_id: str
    factor: str
    category: str
    standard_code: str
    standard_name: str
    method_name: str
    applicability: str


class PublicMethodCardDetail(PublicMethodCardSummary):
    measurement: PublicMeasurement
    requirements: list[PublicRequirement]
    qa_qc: list[PublicQaQcItem]
    evidence_refs: list[PublicEvidenceRef]


class PublicMethodCardListResponse(BaseModel):
    api_version: str
    items: list[PublicMethodCardSummary]
    count: int


class PublicMethodCardDetailResponse(BaseModel):
    api_version: str
    card: PublicMethodCardDetail


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    api_version: str
```

Notes:

- Pydantic response models document the contract.
- Builder returns dicts; FastAPI can validate them against these response models.

Verification:

```powershell
uv run pytest tests/unit -v
```

Expected:

```text
all unit tests pass
```

### Task 5: MethodCard Service

**Files:**

- Create: `enviro-nexus-knowledge/app/services/method_card_service.py`

Implement:

```python
from sqlalchemy.orm import Session

from app.core.public_method_card_builder import (
    build_public_method_card_detail,
    build_public_method_card_summary,
)
from app.db.repositories import (
    get_public_method_card_json,
    list_public_method_card_jsons,
)
from app.schemas.method_card import MethodCard
from app.settings import get_settings


class MethodCardNotFoundError(ValueError):
    error_code = "method_card_not_found"


def list_public_method_cards(session: Session) -> dict:
    settings = get_settings()
    cards = [
        MethodCard.model_validate(payload)
        for payload in list_public_method_card_jsons(session)
    ]
    items = [build_public_method_card_summary(card) for card in cards]
    return {
        "api_version": settings.api_version,
        "items": items,
        "count": len(items),
    }


def get_public_method_card(card_id: str, session: Session) -> dict:
    settings = get_settings()
    payload = get_public_method_card_json(session, card_id)
    if payload is None:
        raise MethodCardNotFoundError("method card is not found or not public")

    card = MethodCard.model_validate(payload)
    return {
        "api_version": settings.api_version,
        "card": build_public_method_card_detail(card),
    }
```

If adding internal debug endpoint, add a separate function:

```python
def get_internal_method_card_debug(card_id: str, session: Session) -> dict:
    ...
```

Do not mix public and debug serialization.

Verification:

```powershell
uv run pytest tests/unit -v
```

Expected:

```text
all unit tests pass
```

### Task 6: MethodCard API Routes and Registration

**Files:**

- Create: `enviro-nexus-knowledge/app/api/routes/method_cards.py`
- Modify: `enviro-nexus-knowledge/app/main.py`

Implement route module:

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.schemas.response import (
    PublicMethodCardDetailResponse,
    PublicMethodCardListResponse,
)
from app.services.method_card_service import (
    MethodCardNotFoundError,
    get_public_method_card,
    list_public_method_cards,
)
from app.settings import get_settings


router = APIRouter()


@router.get("/method-cards", response_model=PublicMethodCardListResponse)
def list_method_cards() -> dict | JSONResponse:
    settings = get_settings()
    try:
        with SessionLocal() as session:
            return list_public_method_cards(session)
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "database_unavailable",
                "message": "database is unavailable",
                "api_version": settings.api_version,
            },
        )


@router.get("/method-cards/{card_id}/public", response_model=PublicMethodCardDetailResponse)
def get_method_card_public(card_id: str) -> dict | JSONResponse:
    settings = get_settings()
    try:
        with SessionLocal() as session:
            return get_public_method_card(card_id, session)
    except MethodCardNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error_code": "method_card_not_found",
                "message": "method card is not found or not public",
                "api_version": settings.api_version,
            },
        )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "database_unavailable",
                "message": "database is unavailable",
                "api_version": settings.api_version,
            },
        )
```

Register route in `app/main.py`:

```python
from app.api.routes.method_cards import router as method_cards_router

app.include_router(method_cards_router, prefix=f"/api/{settings.api_version}")
```

Verification:

```powershell
uv run pytest tests/unit -v
```

Expected:

```text
all unit tests pass
```

### Task 7: Integration Tests for Public API

**Files:**

- Create: `enviro-nexus-knowledge/tests/integration/test_method_cards_api.py`

Use the same real PostgreSQL pattern as `test_factor_query_api.py`.

Test file:

```python
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app
from app.services.import_service import import_seed


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def imported_seed():
    with SessionLocal() as session:
        session.execute(text("DELETE FROM factor_aliases"))
        session.execute(text("DELETE FROM method_cards"))
        session.execute(text("DELETE FROM source_documents"))
        session.execute(text("DELETE FROM knowledge_import_batches"))
        session.commit()

    import_seed(Path("data/seed"), mode="upsert")


def assert_no_internal_fields(payload: dict):
    serialized = str(payload)
    assert "governance" not in serialized
    assert "change_log" not in serialized
    assert "extensions" not in serialized
    assert "source_document" not in serialized
    assert "source_doc_id" not in serialized
    assert "file_path" not in serialized
    assert "metadata" not in serialized
    assert "manual_extract_source" not in serialized
    assert "needs_pdf_check" not in serialized
    assert "evidence_id" not in serialized
    assert "evidence_ids" not in serialized


@pytest.mark.anyio
async def test_list_method_cards_returns_five_public_cards():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/method-cards")

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["count"] == 5
    assert len(body["items"]) == 5
    assert {item["card_id"] for item in body["items"]} == {
        "gas_smoke_blackness_hj1287_2023",
        "gas_thc_methane_nmhc_hj1332_2023",
        "water_colority_hj1182_2021",
        "water_permanganate_index_hj1445_2026",
        "water_ph_hj1147_2020",
    }
    assert_no_internal_fields(body)


@pytest.mark.anyio
async def test_get_public_method_card_returns_ph_detail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/method-cards/water_ph_hj1147_2020/public")

    assert response.status_code == 200
    body = response.json()
    card = body["card"]
    assert body["api_version"] == "v1"
    assert card["card_id"] == "water_ph_hj1147_2020"
    assert card["factor"] == "pH 值"
    assert card["category"] == "水质"
    assert card["standard_code"] == "HJ 1147-2020"
    assert card["standard_name"] == "水质 pH 值的测定 电极法"
    assert card["method_name"] == "电极法"
    assert card["applicability"]
    assert card["measurement"]
    assert card["requirements"]
    assert card["qa_qc"]
    assert card["evidence_refs"]
    assert set(card["evidence_refs"][0].keys()) == {
        "source_title",
        "section",
        "page",
        "summary",
    }
    assert_no_internal_fields(body)


@pytest.mark.anyio
async def test_get_public_method_card_missing_card_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/method-cards/not_exists/public")

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "method_card_not_found",
        "message": "method card is not found or not public",
        "api_version": "v1",
    }


@pytest.mark.anyio
async def test_get_public_method_card_rejects_disabled_or_not_approved_cards():
    with SessionLocal() as session:
        session.execute(
            text(
                "UPDATE method_cards "
                "SET answer_visibility = 'disabled' "
                "WHERE card_id = 'water_ph_hj1147_2020'"
            )
        )
        session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        disabled_response = await client.get("/api/v1/method-cards/water_ph_hj1147_2020/public")
        list_response = await client.get("/api/v1/method-cards")

    assert disabled_response.status_code == 404
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["count"] == 4
    assert "water_ph_hj1147_2020" not in {item["card_id"] for item in body["items"]}

    with SessionLocal() as session:
        session.execute(
            text(
                "UPDATE method_cards "
                "SET answer_visibility = 'enabled', review_status = 'draft' "
                "WHERE card_id = 'water_ph_hj1147_2020'"
            )
        )
        session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        draft_response = await client.get("/api/v1/method-cards/water_ph_hj1147_2020/public")

    assert draft_response.status_code == 404
```

- [ ] Run before implementation:

```powershell
uv run pytest tests/integration/test_method_cards_api.py -v
```

Expected RED:

```text
404 Not Found for /api/v1/method-cards or import errors for missing route
```

- [ ] After route/service/repository implementation, rerun:

```powershell
uv run pytest tests/integration/test_method_cards_api.py -v
```

Expected GREEN:

```text
4 passed
```

### Task 8: Preserve Factor Query Regression Tests

**Files:** no writes unless a regression appears.

Run:

```powershell
uv run pytest tests/integration/test_factor_query_api.py -v
```

Expected:

```text
all factor query tests pass
```

This specifically protects:

```text
POST /api/v1/factors/query response shape remains compatible
COD 怎么测？ remains matched=false
CODMn 怎么测？ remains matched=true
```

If this fails, fix Day 1.6 changes without changing the established factor query public contract.

### Task 9: API Contract Documentation

**Files:**

- Create or update: `enviro-nexus-knowledge/docs/api-contract.md`

Document:

```text
EnviroNexus Knowledge API Contract
Base URL
Authentication: none for local POC
Common response fields
Common errors
GET /api/v1/health
POST /api/v1/factors/query
GET /api/v1/method-cards
GET /api/v1/method-cards/{card_id}/public
Optional internal debug endpoint if implemented
PowerShell curl examples
Postman configuration notes
Frontend integration notes
Non-goals
```

Required curl examples:

```powershell
curl.exe http://127.0.0.1:8010/api/v1/health
```

```powershell
curl.exe -X POST "http://127.0.0.1:8010/api/v1/factors/query" -H "Content-Type: application/json; charset=utf-8" -d '{"query":"CODMn 怎么测？"}'
```

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards"
```

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards/water_ph_hj1147_2020/public"
```

Postman note:

```text
Body -> raw -> JSON
Header -> Content-Type: application/json
Do not use raw Text for JSON request bodies.
```

Explicitly document that public endpoints do not return:

```text
governance
change_log
extensions
source_document
file_path
metadata
evidence_id
evidence_ids
```

### Task 10: Full Verification

Run:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
docker compose up -d postgres
uv run alembic upgrade head
uv run python -m app.services.import_service --seed data/seed --mode upsert
uv run pytest -v
```

Expected:

```text
all tests pass
```

Expected final test count:

```text
35 existing tests + new tests
```

The exact count will depend on whether the public builder unit tests are placed in a new file and whether optional debug endpoint tests are added.

### Task 11: Curl Verification

Start API:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010
```

In another terminal:

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards"
```

Expected summary:

```text
status 200
count = 5
items contains water_ph_hj1147_2020
items contains water_permanganate_index_hj1445_2026
no governance/change_log/extensions/file_path/evidence_ids
```

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards/water_ph_hj1147_2020/public"
```

Expected summary:

```text
status 200
card.card_id = water_ph_hj1147_2020
card.standard_code = HJ 1147-2020
card.measurement exists
card.requirements non-empty
card.qa_qc non-empty
card.evidence_refs non-empty
no governance/change_log/extensions/file_path/evidence_ids
```

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards/not_exists/public"
```

Expected:

```text
status 404
error_code = method_card_not_found
```

Regression curl:

```powershell
curl.exe -X POST "http://127.0.0.1:8010/api/v1/factors/query" -H "Content-Type: application/json; charset=utf-8" -d '{"query":"COD 怎么测？"}'
```

Expected:

```text
matched=false
card_id=null
```

```powershell
curl.exe -X POST "http://127.0.0.1:8010/api/v1/factors/query" -H "Content-Type: application/json; charset=utf-8" -d '{"query":"CODMn 怎么测？"}'
```

Expected:

```text
matched=true
card_id=water_permanganate_index_hj1445_2026
```

### Task 12: Final Safety Check

Run:

```powershell
cd D:\szy\code\my-project\enviro-nexus
git -c core.quotepath=false status --short -- enviro-nexus-api enviro-nexus-web
git -c core.quotepath=false ls-files | rg "(^|/)(__pycache__/|\\.pytest_cache/|.*\\.py[co]$|.*\\.pyd$)"
```

Expected:

```text
enviro-nexus-api/web status output empty
tracked cache scan has no output
```

If cache files exist on disk but are ignored, report that they are ignored and do not delete unless asked.

## 7. Public Serialization Rules

Public APIs must never expose internal fields.

Blocked field names:

```text
governance
review_status
answer_visibility
change_log
extensions
source_document
source_doc_id
file_path
metadata
checksum_sha256
manual_extract_source
needs_pdf_check
evidence_id
evidence_ids
```

Reason:

- `governance`, `review_status`, and `answer_visibility` are publication controls.
- `change_log` and `extensions` are internal governance/data lifecycle details.
- `source_document`, `file_path`, and `metadata` can expose local filesystem structure and extraction state.
- `evidence_id` / `evidence_ids` are internal linkage identifiers, while frontend only needs citation-like display fields.

Implementation rule:

- Do not return `card.model_dump()` directly from public endpoints.
- Always use `public_method_card_builder.py`.

## 8. Visibility Rules

Public endpoints must filter:

```text
review_status = approved
answer_visibility = enabled
```

The following cards must not be public:

```text
review_status in draft/reviewing/rejected
answer_visibility = disabled
missing card_id
```

Response:

```text
404 method_card_not_found
```

For list endpoint:

- Non-public cards are omitted.
- `count` equals number of returned public items.

## 9. Test Matrix

Required tests:

```text
unit: public summary omits internal fields
unit: public detail omits internal fields and returns required fields
integration: GET /api/v1/method-cards returns 5 items
integration: GET /api/v1/method-cards/water_ph_hj1147_2020/public returns public pH detail
integration: missing card returns 404
integration: disabled card not returned by public detail or list
integration: draft card not returned by public detail
integration: factor query existing tests still pass
full: uv run pytest -v passes
```

## 10. Completion Report Format

After implementation, report:

```text
1. 修改/新增文件
2. 新增接口
3. 测试结果
4. curl 验证结果
5. 是否修改 enviro-nexus-api / enviro-nexus-web
6. 遗留问题
```

Use this exact shape:

```text
## Day 1.6 执行结果

### 1. 修改/新增文件
- 修改：
- 新增：

### 2. 新增接口
- GET /api/v1/method-cards
- GET /api/v1/method-cards/{card_id}/public

### 3. 测试结果
- uv run pytest tests/unit -v:
- uv run pytest tests/integration/test_method_cards_api.py -v:
- uv run pytest -v:

### 4. curl 验证结果
- GET /api/v1/method-cards:
- GET /api/v1/method-cards/water_ph_hj1147_2020/public:
- GET /api/v1/method-cards/not_exists/public:
- POST /api/v1/factors/query COD:
- POST /api/v1/factors/query CODMn:

### 5. api/web 是否修改
enviro-nexus-api:
enviro-nexus-web:

### 6. 遗留问题
无 / 有：
```

## 11. Approval Gate

Do not implement until the user explicitly approves this plan.

Approval means:

- Add public MethodCard list/detail APIs.
- Keep factor query contract compatible.
- Keep only approved + enabled cards publicly visible.
- Add `docs/api-contract.md`.
- Keep `enviro-nexus-api` and `enviro-nexus-web` untouched.
- Keep Day 1.6 limited to knowledge service API contract work.
