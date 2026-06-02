import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import v1_router
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.middleware.request_id import RequestIdMiddleware
from app.services.session_store import build_session_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    settings = get_settings()
    app.state.session_store = build_session_store(
        settings.session_store,
        settings.session_ttl_seconds,
        settings.redis_url,
    )
    logger.info(
        "%s v%s 启动 | knowledge_service=%s | session_store=%s",
        settings.app_name,
        settings.app_version,
        settings.knowledge_service_base_url,
        settings.session_store,
    )
    yield


def create_app() -> FastAPI:
    """应用工厂函数。"""
    settings = get_settings()

    # 初始化日志
    setup_logging(log_level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # 注册中间件
    app.add_middleware(RequestIdMiddleware)

    # 注册异常处理器
    register_exception_handlers(app)

    # 注册路由
    app.include_router(v1_router)

    return app


app = create_app()
