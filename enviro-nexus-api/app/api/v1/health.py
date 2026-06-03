from fastapi import APIRouter, Depends, Request

from app.dependencies import get_health_service_dep
from app.schemas.common import COMMON_RESPONSES
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses=COMMON_RESPONSES,
)
async def health_check(
    request: Request,
    health_service: HealthService = Depends(get_health_service_dep),
):
    """健康检查接口：返回 API 与知识服务可用性。"""
    request_id = getattr(request.state, "request_id", None)
    return await health_service.check(request_id=request_id)
