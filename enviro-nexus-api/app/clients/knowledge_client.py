import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import Settings
from app.schemas.knowledge import (
    KnowledgeEvidenceRefItem,
    KnowledgeFactorAnswer,
    KnowledgeFactorQueryPayload,
    KnowledgeMethodCardContent,
    KnowledgeMethodCardIdentity,
    KnowledgeMethodCardPayload,
    KnowledgeRequirementItem,
)

logger = logging.getLogger(__name__)

MOCK_SUPPORTED_FACTORS = {
    "pH": {
        "card_id": "mock_ph",
        "aliases": {"pH", "pH值", "PH", "PH值", "酸碱度"},
    },
    "色度": {
        "card_id": "mock_chroma",
        "aliases": {"色度", "水质色度", "颜色", "铂钴色度"},
    },
    "高锰酸盐指数": {
        "card_id": "mock_codmn",
        "aliases": {"高锰酸盐指数", "CODMn", "耗氧量", "高锰酸盐"},
    },
    "林格曼黑度": {
        "card_id": "mock_ringelmann_blackness",
        "aliases": {"林格曼黑度", "烟气黑度", "黑度", "林格曼烟气黑度"},
    },
    "总烃": {
        "card_id": "mock_thc",
        "aliases": {"总烃", "THC"},
    },
    "甲烷": {
        "card_id": "mock_methane",
        "aliases": {"甲烷", "methane"},
    },
    "非甲烷总烃": {
        "card_id": "mock_nmhc",
        "aliases": {"非甲烷总烃", "NMHC", "非甲烷烃"},
    },
}

MOCK_FACTOR_BY_CARD_ID = {
    data["card_id"]: factor for factor, data in MOCK_SUPPORTED_FACTORS.items()
}


def _normalize_mock_factor(factor_name: str) -> str | None:
    normalized = factor_name.strip()
    if not normalized:
        return None
    for factor, data in MOCK_SUPPORTED_FACTORS.items():
        if normalized in data["aliases"]:
            return factor
    return None


def _mock_factor_query_payload(query: str, factor_name: str) -> KnowledgeFactorQueryPayload:
    factor = _normalize_mock_factor(factor_name)
    if factor is None:
        return KnowledgeFactorQueryPayload(
            matched=False,
            factor=factor_name.strip() or None,
            warnings=["当前为知识库 Mock 数据，未命中该检测因子。"],
        )

    card_id = MOCK_SUPPORTED_FACTORS[factor]["card_id"]
    return KnowledgeFactorQueryPayload(
        matched=True,
        factor=factor,
        matched_alias=factor_name.strip() or factor,
        card_id=card_id,
        answer=KnowledgeFactorAnswer(
            summary=f"{factor}检测方法查询命中，本结果为前端联调 Mock 数据。",
            standard_code="MOCK-STANDARD",
            standard_name=f"{factor}检测方法 Mock 标准",
            method_name=f"{factor}检测 Mock 方法",
            applicability="用于前端联调展示，真实适用范围以知识库服务恢复后的结果为准。",
            requirements=[
                KnowledgeRequirementItem(
                    type="sample",
                    title="样品要求",
                    content="Mock：采样、保存和前处理要求由真实知识库恢复后提供。",
                ),
                KnowledgeRequirementItem(
                    type="quality_control",
                    title="质控要求",
                    content="Mock：建议展示空白、平行样和标准样等质控信息。",
                ),
            ],
            evidence_refs=[
                KnowledgeEvidenceRefItem(
                    evidence_id="mock_ev_001",
                    source_title=f"{factor} Mock 知识库",
                    section="前端联调",
                    summary="该条证据为知识库 Mock 数据，用于验证前端来源展示。",
                    field_path="mock.evidence",
                )
            ],
        ),
        warnings=["当前为知识库 Mock 数据，未调用真实知识库服务。"],
    )


def _mock_method_card_payload(card_id: str) -> KnowledgeMethodCardPayload:
    factor = MOCK_FACTOR_BY_CARD_ID.get(card_id)
    return KnowledgeMethodCardPayload(
        card=KnowledgeMethodCardContent(
            card_id=card_id,
            identity=KnowledgeMethodCardIdentity(factor=factor),
        )
    )


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
        # TODO: 前端联调完成后恢复真实知识库服务调用。
        # url = f"{self._base_url}/api/v1/factors/query"
        # data = await self._request(
        #     "POST",
        #     url,
        #     json={"query": query, "factor_name": factor_name},
        # )
        # return self._validate_payload(KnowledgeFactorQueryPayload, data, url)
        return _mock_factor_query_payload(query, factor_name)

    async def get_method_card(self, card_id: str) -> KnowledgeMethodCardPayload:
        """调用知识服务的方法卡详情接口。"""
        # TODO: 前端联调完成后恢复真实知识库服务调用。
        # url = f"{self._base_url}/api/v1/method-cards/{card_id}"
        # data = await self._request("GET", url)
        # return self._validate_payload(KnowledgeMethodCardPayload, data, url)
        return _mock_method_card_payload(card_id)

    async def health_check(self) -> dict:
        """调用知识服务的健康检查接口。"""
        # TODO: 前端联调完成后恢复真实知识库服务调用。
        # url = f"{self._base_url}/api/v1/health"
        # return await self._request("GET", url)
        return {"success": True, "mock": True}
