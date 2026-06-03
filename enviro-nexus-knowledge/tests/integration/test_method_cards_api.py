import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app
from app.services.import_service import import_seed


PUBLIC_CARD_IDS = {
    "gas_smoke_blackness_hj1287_2023",
    "gas_thc_methane_nmhc_hj1332_2023",
    "water_colority_hj1182_2021",
    "water_permanganate_index_hj1445_2026",
    "water_ph_hj1147_2020",
}

BLOCKED_PUBLIC_FIELDS = [
    "governance",
    "review_status",
    "answer_visibility",
    "change_log",
    "extensions",
    "source_document",
    "source_doc_id",
    "file_path",
    "metadata",
    "checksum_sha256",
    "manual_extract_source",
    "needs_pdf_check",
    "evidence_id",
    "evidence_ids",
]


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


def assert_no_internal_fields(payload: dict) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    for field_name in BLOCKED_PUBLIC_FIELDS:
        assert field_name not in serialized


@pytest.mark.anyio
async def test_list_method_cards_returns_five_public_cards():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/method-cards")

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["count"] == 5
    assert len(body["items"]) == 5
    assert {item["card_id"] for item in body["items"]} == PUBLIC_CARD_IDS
    assert all(
        set(item.keys())
        == {
            "card_id",
            "factor",
            "category",
            "standard_code",
            "standard_name",
            "method_name",
            "applicability",
        }
        for item in body["items"]
    )
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
    list_body = list_response.json()
    assert list_body["count"] == 4
    assert "water_ph_hj1147_2020" not in {item["card_id"] for item in list_body["items"]}

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
