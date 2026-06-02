from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.session import ChatMessage, SessionRecord
from app.services.session_store import InMemorySessionStore


@pytest.mark.asyncio
async def test_save_and_get_roundtrip():
    store = InMemorySessionStore(ttl_seconds=3600)
    record = SessionRecord(
        session_id="s1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        summary="",
        messages=[ChatMessage(role="user", content="hi")],
    )
    await store.save(record)
    loaded = await store.get("s1")
    assert loaded is not None
    assert loaded.messages[0].content == "hi"


@pytest.mark.asyncio
async def test_expired_session_returns_none():
    store = InMemorySessionStore(ttl_seconds=1)
    record = SessionRecord(
        session_id="s2",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        updated_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        summary="",
        messages=[],
    )
    await store.save(record)
    assert await store.get("s2") is None
