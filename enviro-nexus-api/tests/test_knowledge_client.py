import pytest

from app.clients.knowledge_client import KnowledgeClient
from app.config.settings import Settings


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


class CapturingHttpClient:
    def __init__(self, body):
        self.body = body
        self.calls = []

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse(self.body)


@pytest.mark.asyncio
async def test_query_factor_posts_query_to_knowledge():
    http_client = CapturingHttpClient(
        {
            "api_version": "v1",
            "matched": True,
            "factor": "pH",
            "matched_alias": "pH",
            "match_confidence": 1.0,
            "card_id": "water_ph_hj1147_2020",
            "answer": None,
            "warnings": [],
        }
    )
    settings = Settings(knowledge_service_base_url="http://knowledge.test/api/v1")
    client = KnowledgeClient(http_client=http_client, settings=settings)

    payload = await client.query_factor("pH 怎么测？")

    assert http_client.calls == [
        (
            "POST",
            "http://knowledge.test/api/v1/factors/query",
            {"timeout": 10.0, "json": {"query": "pH 怎么测？"}},
        )
    ]
    assert payload.matched is True
    assert payload.factor == "pH"
    assert payload.card_id == "water_ph_hj1147_2020"


@pytest.mark.asyncio
async def test_query_factor_validates_unmatched_response():
    http_client = CapturingHttpClient(
        {
            "api_version": "v1",
            "matched": False,
            "factor": None,
            "matched_alias": None,
            "match_confidence": 0.0,
            "card_id": None,
            "answer": None,
            "warnings": ["当前知识库暂未收录该检测因子，请人工确认后再使用。"],
        }
    )
    settings = Settings(knowledge_service_base_url="http://knowledge.test/api/v1")
    client = KnowledgeClient(http_client=http_client, settings=settings)

    payload = await client.query_factor("COD 怎么测？")

    assert payload.matched is False
    assert payload.factor is None
    assert payload.card_id is None


@pytest.mark.asyncio
async def test_get_method_card_uses_public_detail_endpoint():
    http_client = CapturingHttpClient(
        {
            "api_version": "v1",
            "card": {
                "card_id": "water_ph_hj1147_2020",
                "factor": "pH",
                "category": "water",
                "standard_code": "HJ 1147-2020",
                "standard_name": "水质 pH值的测定",
                "method_name": "电极法",
                "applicability": "适用于水质 pH 的测定。",
                "measurement": {
                    "principle": "玻璃电极法",
                    "instrument": "pH计",
                    "unit": None,
                    "range": None,
                },
                "requirements": [],
                "qa_qc": [],
                "evidence_refs": [],
            },
        }
    )
    settings = Settings(knowledge_service_base_url="http://knowledge.test/api/v1")
    client = KnowledgeClient(http_client=http_client, settings=settings)

    payload = await client.get_method_card("water_ph_hj1147_2020")

    assert http_client.calls[0][0] == "GET"
    assert http_client.calls[0][1] == (
        "http://knowledge.test/api/v1/method-cards/water_ph_hj1147_2020/public"
    )
    assert payload.card is not None
    assert payload.card.card_id == "water_ph_hj1147_2020"
    assert payload.card.factor == "pH"


@pytest.mark.asyncio
async def test_health_check_calls_knowledge_health_endpoint():
    http_client = CapturingHttpClient(
        {
            "status": "ok",
            "service": "enviro-nexus-knowledge",
            "api_version": "v1",
            "database": "ok",
        }
    )
    settings = Settings(knowledge_service_base_url="http://knowledge.test/api/v1")
    client = KnowledgeClient(http_client=http_client, settings=settings)

    payload = await client.health_check()

    assert http_client.calls[0][0] == "GET"
    assert http_client.calls[0][1] == "http://knowledge.test/api/v1/health"
    assert payload["status"] == "ok"
