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


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("query", "expected_card_id", "expected_standard_code"),
    [
        ("pH 怎么测？", "water_ph_hj1147_2020", "HJ 1147-2020"),
        ("水样酸碱度用什么标准？", "water_ph_hj1147_2020", "HJ 1147-2020"),
        ("色度怎么测？", "water_colority_hj1182_2021", "HJ 1182-2021"),
        ("CODMn 怎么测？", "water_permanganate_index_hj1445_2026", "HJ 1445-2026"),
        ("烟气黑度怎么测？", "gas_smoke_blackness_hj1287_2023", "HJ 1287-2023"),
        ("非甲烷总烃怎么测？", "gas_thc_methane_nmhc_hj1332_2023", "HJ 1332-2023"),
    ],
)
async def test_factor_query_matches_day1_5_cards_and_returns_evidence_refs(
    query: str,
    expected_card_id: str,
    expected_standard_code: str,
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/factors/query", json={"query": query})

    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["card_id"] == expected_card_id
    assert body["answer"]["standard_code"] == expected_standard_code
    assert body["answer"]["evidence_refs"]


@pytest.mark.anyio
async def test_factor_query_cod_returns_not_matched_even_when_codmn_exists():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/factors/query", json={"query": "COD 怎么测？"})

    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is False
    assert body["card_id"] is None
    assert body["answer"] is None


@pytest.mark.anyio
async def test_factor_query_codmn_matches_permanganate_index():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/factors/query", json={"query": "CODMn 怎么测？"})

    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["card_id"] == "water_permanganate_index_hj1445_2026"
    assert body["answer"]["standard_code"] == "HJ 1445-2026"


@pytest.mark.anyio
async def test_factor_query_empty_query_returns_business_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/factors/query", json={"query": "   "})

    assert response.status_code == 400
    assert response.json()["error_code"] == "empty_query"
