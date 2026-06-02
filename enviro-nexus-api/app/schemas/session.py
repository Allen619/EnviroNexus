from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class SessionRecord(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    summary: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
