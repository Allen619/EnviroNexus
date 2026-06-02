from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.schemas.common import ErrorDetail, build_error_response


class AppError(Exception):
    """应用异常基类。"""

    def __init__(self, message: str, status_code: int = 500, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class KnowledgeServiceError(AppError):
    """知识服务调用失败。"""

    def __init__(self, message: str = "知识服务调用失败"):
        super().__init__(message=message, status_code=502, code="KNOWLEDGE_SERVICE_ERROR")


class LLMServiceError(AppError):
    """大模型调用失败。"""

    def __init__(self, message: str = "大模型服务调用失败"):
        super().__init__(message=message, status_code=502, code="LLM_SERVICE_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return build_error_response(
            request,
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return build_error_response(
            request,
            code="VALIDATION_ERROR",
            message="请求参数校验失败",
            status_code=422,
            error=ErrorDetail(details=exc.errors()),
        )
