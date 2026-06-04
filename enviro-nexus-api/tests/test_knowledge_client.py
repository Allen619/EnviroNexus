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
async def test_query_factor_uses_mock_without_http_call():
    http_client = CapturingHttpClient()
    settings = Settings(knowledge_service_base_url="http://knowledge.test")
    client = KnowledgeClient(http_client=http_client, settings=settings)

    payload = await client.query_factor("pH 怎么测？", "pH")

    assert http_client.calls == []
    assert payload.matched is True
    assert payload.factor == "pH"
    assert payload.card_id == "mock_ph"


@pytest.mark.asyncio
async def test_query_factor_mock_does_not_match_unsupported_factor():
    http_client = CapturingHttpClient()
    settings = Settings(knowledge_service_base_url="http://knowledge.test")
    client = KnowledgeClient(http_client=http_client, settings=settings)

    payload = await client.query_factor("COD 怎么测？", "COD")

    assert http_client.calls == []
    assert payload.matched is False
    assert payload.factor == "COD"
    assert payload.card_id is None


@pytest.mark.asyncio
async def test_get_method_card_uses_mock_without_http_call():
    http_client = CapturingHttpClient()
    settings = Settings(knowledge_service_base_url="http://knowledge.test")
    client = KnowledgeClient(http_client=http_client, settings=settings)

    payload = await client.get_method_card("mock_water_cod_hj828_2017")

    assert http_client.calls == []
    assert payload.card is not None
    assert payload.card.card_id == "mock_water_cod_hj828_2017"
