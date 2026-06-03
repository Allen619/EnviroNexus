from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ApiResponse
from app.schemas.session import ChatMessage, SessionSummary


class SessionDetailData(BaseModel):
    session_id: str = Field(description="会话 UUID")
    title: str = Field(description="会话标题；首轮 query 完成后由 LLM 生成")
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage] = Field(default_factory=list, description="按时间顺序的消息列表")


class SessionListData(BaseModel):
    items: list[SessionSummary] = Field(description="会话摘要列表")
    total: int = Field(description="总会话数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页条数")


class SessionDeleteData(BaseModel):
    deleted: bool = Field(description="是否已删除")


SessionDetailResponse = ApiResponse[SessionDetailData]
SessionListResponse = ApiResponse[SessionListData]
SessionDeleteResponse = ApiResponse[SessionDeleteData]
