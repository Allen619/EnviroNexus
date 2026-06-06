from datetime import datetime, timezone

import pytest

from app.core.exceptions import SessionNotFoundError
from app.schemas.session import ChatMessage, SessionRecord
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


@pytest.mark.asyncio
async def test_list_sessions_sanitizes_existing_reasoning_title():
    store = InMemorySessionStore()
    now = datetime.now(timezone.utc)
    await store.create(
        SessionRecord(
            session_id="session-1",
            user_id="user-a",
            title="<think>\nThe user is ",
            created_at=now,
            updated_at=now,
            messages=[
                ChatMessage(role="user", content="COD怎么测"),
                ChatMessage(role="assistant", content="与知识库不匹配，请重试"),
            ],
        )
    )
    svc = SessionService(store)

    data = await svc.list_sessions("user-a", page=1, page_size=20)

    assert data.items[0].title == "COD怎么测"


@pytest.mark.asyncio
async def test_list_sessions_uses_first_question_when_title_empty_after_first_turn():
    store = InMemorySessionStore()
    now = datetime.now(timezone.utc)
    await store.create(
        SessionRecord(
            session_id="session-1",
            user_id="user-a",
            title="",
            created_at=now,
            updated_at=now,
            messages=[
                ChatMessage(role="user", content="PH怎么测试"),
                ChatMessage(role="assistant", content="与知识库不匹配，请重试"),
            ],
        )
    )
    svc = SessionService(store)

    data = await svc.list_sessions("user-a", page=1, page_size=20)

    assert data.items[0].title == "PH怎么测试"


@pytest.mark.asyncio
async def test_get_session_sanitizes_existing_reasoning_title():
    store = InMemorySessionStore()
    now = datetime.now(timezone.utc)
    await store.create(
        SessionRecord(
            session_id="session-1",
            user_id="user-a",
            title="<think>\n用户问的是\"PH怎么测试",
            created_at=now,
            updated_at=now,
            messages=[
                ChatMessage(role="user", content="PH怎么测试"),
                ChatMessage(role="assistant", content="与知识库不匹配，请重试"),
            ],
        )
    )
    svc = SessionService(store)

    detail = await svc.get_session("user-a", "session-1")

    assert detail.title == "PH怎么测试"
