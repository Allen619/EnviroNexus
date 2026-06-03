import logging
from datetime import datetime, timezone

import httpx

from app.clients.knowledge_client import KnowledgeClient
from app.schemas.health import HealthData, HealthResponse

logger = logging.getLogger(__name__)


class HealthService:
    """健康检查业务编排。"""

    def __init__(self, knowledge_client: KnowledgeClient):
        self._client = knowledge_client

    async def check(self, request_id: str | None = None) -> HealthResponse:
        """检查 API 与下游知识服务状态。"""
        knowledge_status = "up"
        code = "OK"
        message = "healthy"

        try:
            await self._client.health_check()
        except httpx.HTTPError:
            logger.warning("知识服务健康检查失败")
            knowledge_status = "down"
            code = "DEGRADED"
            message = "API 可用，知识服务不可用"

        return HealthResponse(
            success=True,
            code=code,
            message=message,
            request_id=request_id,
            data=HealthData(api="healthy", knowledge_service=knowledge_status),
            timestamp=datetime.now(timezone.utc),
        )
