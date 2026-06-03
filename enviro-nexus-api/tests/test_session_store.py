from datetime import datetime, timezone

import pytest

from app.schemas.session import ChatMessage, SessionRecord
from app.services.session_store import InMemorySessionStore


def _record(session_id: str, user_id: str) -> SessionRecord:
    now = datetime.now(timezone.utc)
    return SessionRecord(
        session_id=session_id,
        user_id=user_id,
        created_at=now,
        updated_at=now,
        messages=[ChatMessage(role="user", content="hi")],
    )


@pytest.mark.asyncio
async def test_create_and_get_roundtrip():
    store = InMemorySessionStore()
    record = _record("s1", "user-a")
    await store.create(record)
    loaded = await store.get("s1")
    assert loaded is not None
    assert loaded.user_id == "user-a"


@pytest.mark.asyncio
async def test_no_ttl_expiration():
    store = InMemorySessionStore()
    record = _record("s2", "user-a")
    await store.save(record)
    assert await store.get("s2") is not None


@pytest.mark.asyncio
async def test_list_by_user_sorted_by_updated_at_desc():
    store = InMemorySessionStore()
    r1 = _record("s1", "user-a")
    r2 = _record("s2", "user-a")
    await store.create(r1)
    await store.create(r2)
    r1.updated_at = datetime.now(timezone.utc)
    await store.save(r1)
    items, total = await store.list_by_user("user-a", offset=0, limit=10)
    assert total == 2
    assert items[0].session_id == "s1"


@pytest.mark.asyncio
async def test_list_by_user_isolated():
    store = InMemorySessionStore()
    await store.create(_record("s1", "user-a"))
    await store.create(_record("s2", "user-b"))
    items, total = await store.list_by_user("user-a", offset=0, limit=10)
    assert total == 1
    assert items[0].session_id == "s1"


@pytest.mark.asyncio
async def test_delete_removes_session_and_index():
    store = InMemorySessionStore()
    await store.create(_record("s1", "user-a"))
    assert await store.delete("s1") is True
    assert await store.get("s1") is None
    items, total = await store.list_by_user("user-a", offset=0, limit=10)
    assert total == 0
