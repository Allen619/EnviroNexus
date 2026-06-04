import json
from unittest.mock import patch

import pytest

from tests.conftest import DEFAULT_USER_HEADERS

STREAM_BODY = {
    "query": "COD 怎么测？",
    "session_id": "stream-session-1",
    "factor_name": "化学需氧量",
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

    with patch(
        "app.services.chat_query_service.ChatQueryService.query_stream",
        side_effect=fake_stream,
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
    assert mocked_stream.call_args.kwargs["factor_name"] == "化学需氧量"


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
async def test_factor_query_stream_blank_query_422(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        headers=DEFAULT_USER_HEADERS,
        json={"query": "   ", "session_id": "s1", "factor_name": "化学需氧量"},
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_factor_query_stream_missing_factor_name_422(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        headers=DEFAULT_USER_HEADERS,
        json={"query": "COD", "session_id": "stream-session-1"},
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_factor_query_stream_blank_factor_name_422(client):
    resp = await client.post(
        "/api/v1/factors/query/stream",
        headers=DEFAULT_USER_HEADERS,
        json={
            "query": "COD",
            "session_id": "stream-session-1",
            "factor_name": "   ",
        },
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "VALIDATION_ERROR"
