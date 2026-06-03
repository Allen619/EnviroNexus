import pytest

USER_HEADER = {"X-User-Id": "test-user"}


@pytest.mark.asyncio
async def test_create_session(client):
    resp = await client.post("/api/v1/sessions", headers=USER_HEADER)
    assert resp.status_code == 200
    assert resp.json()["data"]["session_id"]


@pytest.mark.asyncio
async def test_missing_user_id_returns_422(client):
    resp = await client.post("/api/v1/sessions")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_and_get_session(client):
    created = await client.post("/api/v1/sessions", headers=USER_HEADER)
    session_id = created.json()["data"]["session_id"]
    listed = await client.get("/api/v1/sessions", headers=USER_HEADER)
    assert listed.json()["data"]["total"] >= 1
    detail = await client.get(f"/api/v1/sessions/{session_id}", headers=USER_HEADER)
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_delete_session(client):
    created = await client.post("/api/v1/sessions", headers=USER_HEADER)
    session_id = created.json()["data"]["session_id"]
    deleted = await client.delete(f"/api/v1/sessions/{session_id}", headers=USER_HEADER)
    assert deleted.json()["data"]["deleted"] is True
    detail = await client.get(f"/api/v1/sessions/{session_id}", headers=USER_HEADER)
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_get_other_user_session_404(client):
    created = await client.post("/api/v1/sessions", headers={"X-User-Id": "owner"})
    session_id = created.json()["data"]["session_id"]
    resp = await client.get(
        f"/api/v1/sessions/{session_id}",
        headers={"X-User-Id": "other"},
    )
    assert resp.status_code == 404
