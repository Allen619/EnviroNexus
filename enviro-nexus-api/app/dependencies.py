from collections.abc import AsyncGenerator

import httpx
from fastapi import Depends, Request

from app.clients.knowledge_client import KnowledgeClient
from app.config.settings import Settings, get_settings
from app.llm.minimax_chat import get_chat_model, get_summarizer_model
from app.services.chat_query_service import ChatQueryService
from app.services.factor_service import FactorService
from app.services.health_service import HealthService
from app.services.session_store import SessionStore


async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """提供 httpx.AsyncClient 生命周期管理。"""
    async with httpx.AsyncClient() as client:
        yield client


def get_knowledge_client(
    http_client: httpx.AsyncClient,
    settings: Settings | None = None,
) -> KnowledgeClient:
    """提供 KnowledgeClient 实例。"""
    if settings is None:
        settings = get_settings()
    return KnowledgeClient(http_client=http_client, settings=settings)


def get_factor_service(knowledge_client: KnowledgeClient) -> FactorService:
    """提供 FactorService 实例。"""
    return FactorService(knowledge_client=knowledge_client)


def get_health_service(knowledge_client: KnowledgeClient) -> HealthService:
    """提供 HealthService 实例。"""
    return HealthService(knowledge_client=knowledge_client)


def get_chat_query_service(
    settings: Settings,
    knowledge_client: KnowledgeClient,
    session_store: SessionStore,
) -> ChatQueryService:
    return ChatQueryService(
        knowledge_client=knowledge_client,
        session_store=session_store,
        chat_model=get_chat_model(settings),
        summarizer=get_summarizer_model(settings),
        max_recent_messages=settings.max_recent_turns,
        char_threshold=settings.compress_char_threshold,
    )


def get_factor_service_dep(
    http_client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> FactorService:
    """FastAPI 依赖：组装 FactorService。"""
    return get_factor_service(get_knowledge_client(http_client, settings))


def get_health_service_dep(
    http_client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> HealthService:
    """FastAPI 依赖：组装 HealthService。"""
    return get_health_service(get_knowledge_client(http_client, settings))


def get_chat_query_service_dep(
    request: Request,
    http_client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> ChatQueryService:
    """FastAPI 依赖：组装 ChatQueryService。"""
    return get_chat_query_service(
        settings,
        get_knowledge_client(http_client, settings),
        request.app.state.session_store,
    )
