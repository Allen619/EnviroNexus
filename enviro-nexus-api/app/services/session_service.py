import uuid
from datetime import datetime, timezone

from app.core.exceptions import SessionNotFoundError
from app.schemas.session import SessionRecord, SessionSummary
from app.schemas.sessions_api import SessionDetailData, SessionListData
from app.services.session_store import SessionStore

PREVIEW_MAX_LEN = 80


def make_preview(content: str) -> str:
    if len(content) <= PREVIEW_MAX_LEN:
        return content
    return content[: PREVIEW_MAX_LEN - 1] + "…"


class SessionService:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    async def _get_owned(self, user_id: str, session_id: str) -> SessionRecord:
        record = await self._store.get(session_id)
        if record is None or record.user_id != user_id:
            raise SessionNotFoundError()
        return record

    def _to_detail(self, record: SessionRecord) -> SessionDetailData:
        return SessionDetailData(
            session_id=record.session_id,
            title=record.title,
            created_at=record.created_at,
            updated_at=record.updated_at,
            messages=record.messages,
        )

    def _to_summary(self, record: SessionRecord) -> SessionSummary:
        preview = ""
        if record.messages:
            preview = make_preview(record.messages[-1].content)
        title = record.title or "新对话"
        return SessionSummary(
            session_id=record.session_id,
            title=title,
            created_at=record.created_at,
            updated_at=record.updated_at,
            preview=preview,
            message_count=len(record.messages),
        )

    async def create_session(self, user_id: str) -> SessionDetailData:
        now = datetime.now(timezone.utc)
        record = SessionRecord(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        await self._store.create(record)
        return self._to_detail(record)

    async def list_sessions(
        self, user_id: str, page: int, page_size: int
    ) -> SessionListData:
        offset = (page - 1) * page_size
        records, total = await self._store.list_by_user(user_id, offset, page_size)
        return SessionListData(
            items=[self._to_summary(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_session(self, user_id: str, session_id: str) -> SessionDetailData:
        record = await self._get_owned(user_id, session_id)
        return self._to_detail(record)

    async def delete_session(self, user_id: str, session_id: str) -> bool:
        await self._get_owned(user_id, session_id)
        return await self._store.delete(session_id)
