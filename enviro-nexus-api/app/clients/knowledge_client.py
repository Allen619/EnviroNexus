import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import Settings
from app.schemas.knowledge import (
    KnowledgeFactorQueryPayload,
    KnowledgeMethodCardPayload,
)

logger = logging.getLogger(__name__)


class KnowledgeClient:
    """封装对 enviro-nexus-knowledge 知识服务的 HTTP 调用。"""

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings):
        self._client = http_client
        self._base_url = settings.knowledge_service_base_url.rstrip("/")
        self._timeout = settings.knowledge_service_timeout

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict:
        try:
            response = await self._client.request(
                method,
                url,
                timeout=self._timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.error("知识服务调用超时: url=%s", url)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "知识服务返回错误: url=%s status=%d",
                url,
                e.response.status_code,
            )
            raise
        except httpx.RequestError as e:
            logger.error("知识服务请求失败: url=%s error=%s", url, str(e))
            raise

    def _validate_payload(self, model_cls: type, data: dict, url: str):
        try:
            return model_cls.model_validate(data)
        except ValidationError:
            logger.exception("知识服务响应格式无效: url=%s", url)
            raise ValueError("知识服务响应格式无效") from None

    async def query_factor(self, query: str, factor_name: str) -> KnowledgeFactorQueryPayload:
        """调用知识服务的因子查询接口。"""
        url = f"{self._base_url}/api/v1/factors/query"
        data = await self._request(
            "POST",
            url,
            json={"query": query, "factor_name": factor_name},
        )
        return self._validate_payload(KnowledgeFactorQueryPayload, data, url)

    async def get_method_card(self, card_id: str) -> KnowledgeMethodCardPayload:
        """调用知识服务的方法卡详情接口。"""
        url = f"{self._base_url}/api/v1/method-cards/{card_id}"
        data = await self._request("GET", url)
        return self._validate_payload(KnowledgeMethodCardPayload, data, url)

    async def health_check(self) -> dict:
        """调用知识服务的健康检查接口。"""
        url = f"{self._base_url}/api/v1/health"
        return await self._request("GET", url)
