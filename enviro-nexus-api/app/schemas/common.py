from datetime import datetime, timedelta, timezone
from typing import Generic, TypeVar

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_serializer

T = TypeVar("T")

API_VERSION = "v1"
# 东八区（中国标准时间），使用固定偏移以兼容无 tzdata 的 Windows 环境
DISPLAY_TIMEZONE = timezone(timedelta(hours=8))
DATETIME_DISPLAY_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_display_datetime(dt: datetime) -> str:
    """将 datetime 格式化为年月日时分秒（YYYY-MM-DD HH:MM:SS，东八区）。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(DISPLAY_TIMEZONE)
    return local.replace(microsecond=0).strftime(DATETIME_DISPLAY_FORMAT)


class ErrorDetail(BaseModel):
    details: list[dict] | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    code: str
    message: str
    api_version: str = API_VERSION
    request_id: str | None = None
    data: T | None = None
    error: ErrorDetail | None = None
    timestamp: datetime

    @field_serializer("timestamp")
    @classmethod
    def serialize_timestamp(cls, v: datetime) -> str:
        return format_display_datetime(v)


class ErrorResponse(ApiResponse[None]):
    """统一错误响应模型，用于 OpenAPI 文档中 4xx/5xx 的响应声明。"""

    success: bool = False


COMMON_RESPONSES: dict[int, dict] = {
    422: {"model": ErrorResponse, "description": "请求参数校验失败"},
    502: {"model": ErrorResponse, "description": "知识服务调用失败"},
}


def build_error_response(
    request: Request,
    *,
    code: str,
    message: str,
    status_code: int,
    error: ErrorDetail | None = None,
    api_version: str = API_VERSION,
) -> JSONResponse:
    """构建统一错误 JSON 响应。"""
    body = ErrorResponse(
        success=False,
        code=code,
        message=message,
        api_version=api_version,
        request_id=getattr(request.state, "request_id", None),
        data=None,
        error=error,
        timestamp=datetime.now(timezone.utc),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))
