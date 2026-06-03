import httpx
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_check_all_up(client):
    """测试健康检查 - API 与知识服务均可用。"""
    with patch(
        "app.clients.knowledge_client.KnowledgeClient.health_check",
        new_callable=AsyncMock,
        return_value={"success": True},
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["code"] == "OK"
    assert data["api_version"] == "v1"
    assert "request_id" in data
    assert data["data"]["api"] == "healthy"
    assert data["data"]["knowledge_service"] == "up"
    assert len(data["timestamp"]) == 19  # YYYY-MM-DD HH:MM:SS
    assert data["timestamp"][10] == " "


@pytest.mark.asyncio
async def test_health_check_knowledge_degraded(client):
    """测试健康检查 - 知识服务不可用时返回 degraded。"""
    with patch(
        "app.clients.knowledge_client.KnowledgeClient.health_check",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("connection refused"),
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["code"] == "DEGRADED"
    assert data["data"]["knowledge_service"] == "down"
