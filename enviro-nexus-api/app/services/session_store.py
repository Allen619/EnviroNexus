from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.session import SessionRecord


class SessionStore(ABC):
    @abstractmethod
    async def create(self, record: SessionRecord) -> None: ...

    @abstractmethod
    async def get(self, session_id: str) -> SessionRecord | None: ...

    @abstractmethod
    async def save(self, record: SessionRecord) -> None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> bool: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> tuple[list[SessionRecord], int]: ...


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._data: dict[str, SessionRecord] = {}
        self._user_index: dict[str, list[str]] = {}

    def _touch_index(self, record: SessionRecord) -> None:
        ids = self._user_index.setdefault(record.user_id, [])
        if record.session_id in ids:
            ids.remove(record.session_id)
        ids.insert(0, record.session_id)

    async def create(self, record: SessionRecord) -> None:
        self._data[record.session_id] = record
        self._touch_index(record)

    async def get(self, session_id: str) -> SessionRecord | None:
        return self._data.get(session_id)

    async def save(self, record: SessionRecord) -> None:
        self._data[record.session_id] = record
        self._touch_index(record)

    async def delete(self, session_id: str) -> bool:
        record = self._data.pop(session_id, None)
        if record is None:
            return False
        ids = self._user_index.get(record.user_id, [])
        if session_id in ids:
            ids.remove(session_id)
        return True

    async def list_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> tuple[list[SessionRecord], int]:
        ids = self._user_index.get(user_id, [])
        total = len(ids)
        slice_ids = ids[offset : offset + limit]
        records = [self._data[sid] for sid in slice_ids if sid in self._data]
        return records, total


class RedisSessionStore(SessionStore):
    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis

        self._client = redis.from_url(redis_url, decode_responses=True)

    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _user_key(self, user_id: str) -> str:
        return f"user:{user_id}:sessions"

    async def create(self, record: SessionRecord) -> None:
        await self.save(record)

    async def get(self, session_id: str) -> SessionRecord | None:
        raw = await self._client.get(self._session_key(session_id))
        if not raw:
            return None
        return SessionRecord.model_validate_json(raw)

    async def save(self, record: SessionRecord) -> None:
        ts = record.updated_at.timestamp()
        pipe = self._client.pipeline()
        pipe.set(self._session_key(record.session_id), record.model_dump_json())
        pipe.zadd(self._user_key(record.user_id), {record.session_id: ts})
        await pipe.execute()

    async def delete(self, session_id: str) -> bool:
        record = await self.get(session_id)
        if record is None:
            return False
        pipe = self._client.pipeline()
        pipe.delete(self._session_key(session_id))
        pipe.zrem(self._user_key(record.user_id), session_id)
        await pipe.execute()
        return True

    async def list_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> tuple[list[SessionRecord], int]:
        key = self._user_key(user_id)
        total = await self._client.zcard(key)
        ids = await self._client.zrevrange(key, offset, offset + limit - 1)
        records: list[SessionRecord] = []
        for sid in ids:
            rec = await self.get(sid)
            if rec:
                records.append(rec)
        return records, total


def build_session_store(store_type: str, redis_url: str) -> SessionStore:
    if store_type == "redis":
        return RedisSessionStore(redis_url=redis_url)
    return InMemorySessionStore()
