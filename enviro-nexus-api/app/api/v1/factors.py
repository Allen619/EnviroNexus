from fastapi import APIRouter, Depends, Request

from app.dependencies import get_chat_query_service_dep, get_factor_service_dep
from app.schemas.chat_query import FactorQueryRequest, FactorQueryResponse
from app.schemas.common import COMMON_RESPONSES
from app.schemas.factor_query import MethodCardResponse
from app.services.chat_query_service import ChatQueryService
from app.services.factor_service import FactorService

router = APIRouter()


@router.post(
    "/factors/query",
    response_model=FactorQueryResponse,
    responses={
        200: {
            "description": "查询成功；未命中时 code 为 FACTOR_NOT_FOUND，success 仍为 true",
        },
        **COMMON_RESPONSES,
    },
)
async def query_factor(
    body: FactorQueryRequest,
    request: Request,
    chat_service: ChatQueryService = Depends(get_chat_query_service_dep),
):
    """因子查询：会话式自然语言回答 + 知识库引用来源。"""
    request_id = getattr(request.state, "request_id", None)
    return await chat_service.query(
        query=body.query,
        request_id=request_id,
        session_id=body.session_id,
    )


@router.get(
    "/method-cards/{card_id}",
    response_model=MethodCardResponse,
    responses=COMMON_RESPONSES,
)
async def get_method_card(
    card_id: str,
    request: Request,
    factor_service: FactorService = Depends(get_factor_service_dep),
):
    """方法卡详情接口：已知 card_id 查看完整方法卡。"""
    request_id = getattr(request.state, "request_id", None)
    return await factor_service.get_method_card(card_id=card_id, request_id=request_id)
