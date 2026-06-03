from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chat_query import SourceItem


class ChatMessage(BaseModel):
    role: str = Field(description="消息角色：user | assistant")
    content: str = Field(description="消息正文")
    sources: list[SourceItem] = Field(
        default_factory=list,
        description="知识库引用（仅 assistant 消息有值）",
    )


class SessionRecord(BaseModel):
    session_id: str
    user_id: str
    title: str = ""
    created_at: datetime
    updated_at: datetime
    summary: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)


class SessionSummary(BaseModel):
    session_id: str
    title: str = Field(description="列表展示标题；空时显示「新对话」")
    created_at: datetime
    updated_at: datetime
    preview: str = Field(default="", description="最后一条消息截断预览")
    message_count: int = Field(default=0, description="消息条数")
