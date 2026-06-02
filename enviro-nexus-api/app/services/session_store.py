from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.schemas.session import SessionRecord


class SessionStore(ABC):
    @abstractmethod
    async def get(self, session_id: str) -> SessionRecord | None: ...

    @abstractmethod
    async def save(self, record: SessionRecord) -> None: ...


class InMemorySessionStore(SessionStore):
    def __init__(self, ttl_seconds: int = 86400) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, SessionRecord] = {}

    def _is_expired(self, record: SessionRecord) -> bool:
        now = datetime.now(timezone.utc)
        updated = record.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return (now - updated).total_seconds() > self._ttl

    async def get(self, session_id: str) -> SessionRecord | None:
        record = self._data.get(session_id)
        if record is None:
            return None
        if self._is_expired(record):
            del self._data[session_id]
            return None
        return record

    async def save(self, record: SessionRecord) -> None:
        self._data[record.session_id] = record


class RedisSessionStore(SessionStore):
    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        import redis.asyncio as redis

        self._client = redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def get(self, session_id: str) -> SessionRecord | None:
        raw = await self._client.get(self._key(session_id))
        if not raw:
            return None
        return SessionRecord.model_validate_json(raw)

    async def save(self, record: SessionRecord) -> None:
        await self._client.set(
            self._key(record.session_id),
            record.model_dump_json(),
            ex=self._ttl,
        )


def build_session_store(store_type: str, ttl_seconds: int, redis_url: str) -> SessionStore:
    if store_type == "redis":
        return RedisSessionStore(redis_url=redis_url, ttl_seconds=ttl_seconds)
    return InMemorySessionStore(ttl_seconds=ttl_seconds)
