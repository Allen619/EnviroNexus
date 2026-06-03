from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request

from app.dependencies import get_session_service_dep, get_user_id
from app.schemas.common import COMMON_RESPONSES
from app.schemas.sessions_api import (
    SessionDeleteData,
    SessionDeleteResponse,
    SessionDetailResponse,
    SessionListResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions")


@router.post(
    "",
    response_model=SessionDetailResponse,
    responses={
        200: {"description": "创建成功，返回空会话（messages 为空）"},
        **COMMON_RESPONSES,
    },
    summary="创建新会话",
)
async def create_session(
    request: Request,
    user_id: str = Depends(get_user_id),
    session_service: SessionService = Depends(get_session_service_dep),
):
    """创建空会话（「新对话」）。

    需请求头 `X-User-Id`。返回 `session_id` 后，再调用 `POST /api/v1/factors/query` 发送首条消息。
    """
    detail = await session_service.create_session(user_id)
    return SessionDetailResponse(
        success=True,
        code="OK",
        message="创建成功",
        request_id=getattr(request.state, "request_id", None),
        data=detail,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "",
    response_model=SessionListResponse,
    responses={
        200: {"description": "返回当前用户的历史会话列表，按 updated_at 降序"},
        **COMMON_RESPONSES,
    },
    summary="历史会话列表",
)
async def list_sessions(
    request: Request,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    user_id: str = Depends(get_user_id),
    session_service: SessionService = Depends(get_session_service_dep),
):
    """获取当前用户的历史会话列表（侧边栏）。

    列表项含 `title`、`preview`（最后一条消息截断）、`message_count`。
    """
    data = await session_service.list_sessions(user_id, page, page_size)
    return SessionListResponse(
        success=True,
        code="OK",
        message="查询成功",
        request_id=getattr(request.state, "request_id", None),
        data=data,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    responses={
        200: {"description": "返回完整会话，含全部 messages 与 assistant 的 sources"},
        **COMMON_RESPONSES,
    },
    summary="会话详情",
)
async def get_session(
    session_id: str,
    request: Request,
    user_id: str = Depends(get_user_id),
    session_service: SessionService = Depends(get_session_service_dep),
):
    """获取指定会话的完整消息历史。

    会话不存在或不属于当前用户时返回 404（`SESSION_NOT_FOUND`）。
    """
    detail = await session_service.get_session(user_id, session_id)
    return SessionDetailResponse(
        success=True,
        code="OK",
        message="查询成功",
        request_id=getattr(request.state, "request_id", None),
        data=detail,
        timestamp=datetime.now(timezone.utc),
    )


@router.delete(
    "/{session_id}",
    response_model=SessionDeleteResponse,
    responses={
        200: {"description": "删除成功"},
        **COMMON_RESPONSES,
    },
    summary="删除会话",
)
async def delete_session(
    session_id: str,
    request: Request,
    user_id: str = Depends(get_user_id),
    session_service: SessionService = Depends(get_session_service_dep),
):
    """删除指定会话及其索引。

    会话不存在或不属于当前用户时返回 404（`SESSION_NOT_FOUND`）。
    """
    await session_service.delete_session(user_id, session_id)
    return SessionDeleteResponse(
        success=True,
        code="OK",
        message="删除成功",
        request_id=getattr(request.state, "request_id", None),
        data=SessionDeleteData(deleted=True),
        timestamp=datetime.now(timezone.utc),
    )
