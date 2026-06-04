import pytest

from app.core.exceptions import SessionNotFoundError
from app.services.session_service import SessionService, make_preview
from app.services.session_store import InMemorySessionStore


def test_make_preview_truncates():
    assert make_preview("a" * 100).endswith("…")
    assert len(make_preview("short")) <= 80


@pytest.mark.asyncio
async def test_create_session_empty():
    store = InMemorySessionStore()
    svc = SessionService(store)
    detail = await svc.create_session("user-a")
    assert detail.session_id
    assert detail.messages == []
    assert detail.title == ""


@pytest.mark.asyncio
async def test_get_session_wrong_user_raises():
    store = InMemorySessionStore()
    svc = SessionService(store)
    detail = await svc.create_session("user-a")
    with pytest.raises(SessionNotFoundError):
        await svc.get_session("user-b", detail.session_id)


@pytest.mark.asyncio
async def test_list_sessions_maps_summary():
    store = InMemorySessionStore()
    svc = SessionService(store)
    await svc.create_session("user-a")
    data = await svc.list_sessions("user-a", page=1, page_size=20)
    assert data.total == 1
    assert data.items[0].message_count == 0


@pytest.mark.asyncio
async def test_delete_session():
    store = InMemorySessionStore()
    svc = SessionService(store)
    detail = await svc.create_session("user-a")
    assert await svc.delete_session("user-a", detail.session_id) is True
    with pytest.raises(SessionNotFoundError):
        await svc.get_session("user-a", detail.session_id)
