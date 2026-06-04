import json
from unittest.mock import patch

import pytest

import app.dependencies as dependencies
from app.config.settings import Settings, get_settings
from app.main import app
from tests.conftest import DEFAULT_USER_HEADERS

REAL_GET_CHAT_QUERY_SERVICE = dependencies.get_chat_query_service

STREAM_BODY = {
    "query": "COD 怎么测？",
    "session_id": "stream-session-1",
}


def parse_sse_events(raw: str) -> list[tuple[str, dict]]:
    events = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = "message"
        data = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data = json.loads(line.removeprefix("data:").strip())
        if data is not None:
            events.append((event_type, data))
    return events


@pytest.mark.asyncio
async def test_factor_query_stream_returns_sse(client):
    async def fake_stream(*args, **kwargs):
        yield "event: meta\ndata: {\"session_id\":\"s1\",\"matched\":true,\"code\":\"OK\",\"sources\":[]}\n\n"
        yield "event: token\ndata: {\"content\":\"你好\"}\n\n"
        yield "event: done\ndata: {\"session_id\":\"s1\",\"reply\":\"你好\"}\n\n"

    async def fake_open_stream(*args, **kwargs):
        return fake_stream()

    with patch(
        "app.services.chat_query_service.ChatQueryService.open_query_stream",
        side_effect=fake_open_stream,
    ) as mocked_stream:
        resp = await client.post(
            "/api/v1/factors/query/stream",
            headers=DEFAULT_USER_HEADERS,
            json=STREAM_BODY,
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = parse_sse_events(resp.text)
    assert [t for t, _ in events] == ["meta", "token", "done"]
    assert "factor_name" not in mocked_stream.call_args.kwargs


@pytest.mark.asyncio
async def test_factor_query_stream_missing_user_id_422_json(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        json=STREAM_BODY,
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_factor_query_stream_missing_session_returns_404_json(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        headers=DEFAULT_USER_HEADERS,
        json={**STREAM_BODY, "session_id": "missing-session"},
    )

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_factor_query_stream_blank_query_422(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        headers=DEFAULT_USER_HEADERS,
        json={"query": "   ", "session_id": "s1", "factor_name": "化学需氧量"},
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_factor_query_stream_does_not_require_factor_name(client):
    async def fake_stream(*args, **kwargs):
        yield "event: done\ndata: {\"session_id\":\"s1\",\"reply\":\"ok\"}\n\n"

    async def fake_open_stream(*args, **kwargs):
        return fake_stream()

    with patch(
        "app.services.chat_query_service.ChatQueryService.open_query_stream",
        side_effect=fake_open_stream,
    ):
        resp = await client.post(
            "/api/v1/factors/query/stream",
            headers=DEFAULT_USER_HEADERS,
            json={"query": "COD", "session_id": "stream-session-1"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")


@pytest.mark.asyncio
async def test_factor_query_stream_ignores_legacy_blank_factor_name(client):
    async def fake_stream(*args, **kwargs):
        yield "event: done\ndata: {\"session_id\":\"s1\",\"reply\":\"ok\"}\n\n"

    async def fake_open_stream(*args, **kwargs):
        return fake_stream()

    with patch(
        "app.services.chat_query_service.ChatQueryService.open_query_stream",
        side_effect=fake_open_stream,
    ):
        resp = await client.post(
            "/api/v1/factors/query/stream",
            headers=DEFAULT_USER_HEADERS,
            json={
                "query": "COD",
                "session_id": "stream-session-1",
                "factor_name": "   ",
            },
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

@pytest.mark.asyncio
async def test_factor_query_stream_missing_minimax_api_key_returns_502_json(client, monkeypatch):
    monkeypatch.setattr("app.dependencies.get_chat_query_service", REAL_GET_CHAT_QUERY_SERVICE)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_ADMIN_KEY", raising=False)
    app.dependency_overrides[get_settings] = lambda: Settings(minimax_api_key="")
    try:
        resp = await client.post(
            "/api/v1/factors/query/stream",
            headers=DEFAULT_USER_HEADERS,
            json=STREAM_BODY,
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert resp.status_code == 502
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "LLM_SERVICE_ERROR"
