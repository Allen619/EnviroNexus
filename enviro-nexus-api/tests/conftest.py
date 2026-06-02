import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config.settings import get_settings
from app.main import app
from app.services.session_store import build_session_store


@pytest.fixture(autouse=True)
def init_session_store():
    """测试环境注入与 lifespan 一致的 SessionStore。"""
    settings = get_settings()
    app.state.session_store = build_session_store(
        settings.session_store,
        settings.session_ttl_seconds,
        settings.redis_url,
    )
    yield


@pytest.fixture(autouse=True)
def stub_chat_query_service_factory(monkeypatch):
    """集成测试使用 Fake LLM，不实例化 MiniMax/OpenAI 客户端。"""
    from app.services.chat_query_service import ChatQueryService

    def factory(settings, knowledge_client, session_store):
        return ChatQueryService(
            knowledge_client=knowledge_client,
            session_store=session_store,
            chat_model=FakeListChatModel(responses=["测试回复"]),
            summarizer=FakeListChatModel(responses=["测试摘要"]),
            max_recent_messages=settings.max_recent_turns,
            char_threshold=settings.compress_char_threshold,
        )

    monkeypatch.setattr("app.dependencies.get_chat_query_service", factory)


@pytest.fixture
async def client():
    """提供异步测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
