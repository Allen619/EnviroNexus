import logging
from datetime import datetime, timezone

import httpx

from app.clients.knowledge_client import KnowledgeClient
from app.core.exceptions import KnowledgeServiceError
from app.schemas.factor_query import (
    MethodCardContent,
    MethodCardData,
    MethodCardIdentity,
    MethodCardResponse,
)

logger = logging.getLogger(__name__)


class FactorService:
    """方法卡等业务编排。"""

    def __init__(self, knowledge_client: KnowledgeClient):
        self._client = knowledge_client

    async def get_method_card(self, card_id: str, request_id: str | None = None) -> MethodCardResponse:
        """获取方法卡详情。"""
        try:
            payload = await self._client.get_method_card(card_id)
        except (httpx.HTTPError, ValueError):
            logger.exception("方法卡查询失败: card_id=%s", card_id)
            raise KnowledgeServiceError("知识服务调用失败，请稍后重试")

        card = None
        if payload.card is not None:
            identity = None
            factor = payload.card.factor
            if payload.card.identity is not None:
                factor = payload.card.identity.factor or factor
            if factor is not None:
                identity = MethodCardIdentity(factor=factor)
            card = MethodCardContent(
                card_id=payload.card.card_id,
                identity=identity,
            )

        return MethodCardResponse(
            success=True,
            code="OK",
            message="查询成功",
            request_id=request_id,
            data=MethodCardData(card=card),
            timestamp=datetime.now(timezone.utc),
        )
