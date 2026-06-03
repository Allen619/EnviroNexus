from pydantic import BaseModel, Field

from app.schemas.chat_query import SourceItem


class StreamMetaEvent(BaseModel):
    session_id: str
    matched: bool
    factor: str | None = None
    matched_alias: str | None = None
    card_id: str | None = None
    sources: list[SourceItem] = Field(default_factory=list)
    code: str  # OK | FACTOR_NOT_FOUND


class StreamTokenEvent(BaseModel):
    content: str


class StreamDoneEvent(BaseModel):
    session_id: str
    reply: str


class StreamErrorEvent(BaseModel):
    code: str
    message: str
