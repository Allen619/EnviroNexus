from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_query_service_dep, get_factor_service_dep, get_user_id
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
    summary="会话内因子查询",
)
async def query_factor(
    body: FactorQueryRequest,
    request: Request,
    chat_service: ChatQueryService = Depends(get_chat_query_service_dep),
    user_id: str = Depends(get_user_id),
):
    """在已有会话内发送消息并获取 AI 回复。

    **前置条件**：先调用 `POST /api/v1/sessions` 创建会话，再携带返回的 `session_id`。

    **请求头**：`X-User-Id`（必填，与会话归属一致）。

    **行为**：基于会话历史 + 知识库检索生成 `reply`；assistant 消息的 `sources` 会持久化到会话中。
    无效或不属于当前用户的 `session_id` 返回 404。
    """
    request_id = getattr(request.state, "request_id", None)
    return await chat_service.query(
        query=body.query,
        request_id=request_id,
        session_id=body.session_id,
        user_id=user_id,
    )


@router.post(
    "/factors/query/stream",
    responses={
        200: {
            "description": "SSE 流式响应（text/event-stream）；流前错误仍为 JSON",
            "content": {"text/event-stream": {}},
        },
        **COMMON_RESPONSES,
    },
    summary="会话内因子查询（流式）",
)
async def query_factor_stream(
    body: FactorQueryRequest,
    chat_service: ChatQueryService = Depends(get_chat_query_service_dep),
    user_id: str = Depends(get_user_id),
):
    """与 POST /factors/query 相同请求体与鉴权；响应为 SSE。"""
    stream = await chat_service.open_query_stream(
        query=body.query,
        session_id=body.session_id,
        user_id=user_id,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
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
