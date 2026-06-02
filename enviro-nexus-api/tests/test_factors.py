import httpx
import pytest
from unittest.mock import AsyncMock, patch

from app.core.exceptions import KnowledgeServiceError, LLMServiceError
from app.schemas.chat_query import (
    FactorQueryData,
    FactorQueryResponse,
    SourceItem,
)
from app.schemas.factor_query import (
    MethodCardContent,
    MethodCardData,
    MethodCardIdentity,
    MethodCardResponse,
)


@pytest.mark.asyncio
async def test_factor_query_matched(client):
    """测试因子查询 - 命中场景。"""
    mock_response = FactorQueryResponse(
        success=True,
        code="OK",
        message="查询成功",
        data=FactorQueryData(
            session_id="test-session",
            matched=True,
            reply="化学需氧量可采用 HJ 828-2017 重铬酸盐法测定。",
            factor="化学需氧量",
            card_id="water_cod_hj828_2017",
            sources=[
                SourceItem(
                    source_title="HJ 828-2017",
                    section="适用范围",
                    summary="该标准说明了化学需氧量测定方法的适用范围。",
                )
            ],
            warnings=[],
        ),
        timestamp="2026-06-02 08:00:00",
    )

    with patch(
        "app.services.chat_query_service.ChatQueryService.query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.post(
            "/api/v1/factors/query",
            json={"query": "COD 怎么测？"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["code"] == "OK"
    assert data["data"]["session_id"] == "test-session"
    assert data["data"]["matched"] is True
    assert data["data"]["reply"]
    assert data["data"]["sources"][0]["source_title"] == "HJ 828-2017"


@pytest.mark.asyncio
async def test_factor_query_not_matched(client):
    """测试因子查询 - 未命中场景（FACTOR_NOT_FOUND 契约）。"""
    mock_response = FactorQueryResponse(
        success=True,
        code="FACTOR_NOT_FOUND",
        message="当前知识库暂未收录该检测因子",
        data=FactorQueryData(
            session_id="test-session-2",
            matched=False,
            reply="当前知识库暂未收录该检测因子，请人工确认后再使用。",
            factor=None,
            sources=[],
            warnings=[],
        ),
        timestamp="2026-06-02 08:00:00",
    )

    with patch(
        "app.services.chat_query_service.ChatQueryService.query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.post(
            "/api/v1/factors/query",
            json={"query": "不存在的因子"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["code"] == "FACTOR_NOT_FOUND"
    assert data["data"]["matched"] is False
    assert data["data"]["sources"] == []


@pytest.mark.asyncio
async def test_factor_query_validation_422(client):
    """测试因子查询 - 空 query 返回 422。"""
    response = await client.post("/api/v1/factors/query", json={"query": ""})

    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_factor_query_knowledge_service_error_502(client):
    """测试因子查询 - 知识服务失败返回 502。"""
    with patch(
        "app.services.chat_query_service.ChatQueryService.query",
        new_callable=AsyncMock,
        side_effect=KnowledgeServiceError("知识服务调用失败，请稍后重试"),
    ):
        response = await client.post(
            "/api/v1/factors/query",
            json={"query": "COD"},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["code"] == "KNOWLEDGE_SERVICE_ERROR"


@pytest.mark.asyncio
async def test_factor_query_llm_service_error_502(client):
    """测试因子查询 - 大模型失败返回 502。"""
    with patch(
        "app.services.chat_query_service.ChatQueryService.query",
        new_callable=AsyncMock,
        side_effect=LLMServiceError("大模型服务调用失败，请稍后重试"),
    ):
        response = await client.post(
            "/api/v1/factors/query",
            json={"query": "COD"},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["code"] == "LLM_SERVICE_ERROR"


@pytest.mark.asyncio
async def test_factor_query_upstream_timeout_502(client):
    """测试因子查询 - 上游超时经 Service 转为 502。"""
    with patch(
        "app.clients.knowledge_client.KnowledgeClient.query_factor",
        new_callable=AsyncMock,
        side_effect=httpx.TimeoutException("timeout"),
    ):
        response = await client.post(
            "/api/v1/factors/query",
            json={"query": "COD"},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["code"] == "KNOWLEDGE_SERVICE_ERROR"


@pytest.mark.asyncio
async def test_factor_query_multi_turn_session(client):
    """多轮请求同一 session_id 可续聊（memory store 跨请求）。"""
    from app.schemas.knowledge import KnowledgeFactorQueryPayload

    payload = KnowledgeFactorQueryPayload(matched=False)
    with patch(
        "app.clients.knowledge_client.KnowledgeClient.query_factor",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        first = await client.post("/api/v1/factors/query", json={"query": "第一轮"})
        second = await client.post(
            "/api/v1/factors/query",
            json={"query": "第二轮", "session_id": first.json()["data"]["session_id"]},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["session_id"] == first.json()["data"]["session_id"]
    assert "会话已过期" not in " ".join(second.json()["data"].get("warnings", []))


@pytest.mark.asyncio
async def test_method_card_detail(client):
    """测试方法卡详情接口。"""
    mock_response = MethodCardResponse(
        success=True,
        code="OK",
        message="查询成功",
        data=MethodCardData(
            card=MethodCardContent(
                card_id="water_cod_hj828_2017",
                identity=MethodCardIdentity(factor="化学需氧量"),
            ),
        ),
        timestamp="2026-06-02 08:00:00",
    )

    with patch(
        "app.services.factor_service.FactorService.get_method_card",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/v1/method-cards/water_cod_hj828_2017")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["card"]["card_id"] == "water_cod_hj828_2017"
