from pydantic import BaseModel

from app.schemas.common import ApiResponse


class HealthData(BaseModel):
    """健康检查数据。"""

    api: str = "healthy"
    knowledge_service: str = "up"


HealthResponse = ApiResponse[HealthData]
