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
    assert kwargs["json"] == {
        "query": "COD 怎么测？",
        "factor_name": "化学需氧量",
    }
