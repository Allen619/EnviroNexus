import json
from app.utils.sse import format_sse

def test_format_sse_produces_valid_frame():
    frame = format_sse("meta", {"session_id": "s1", "matched": True})
    assert frame.startswith("event: meta\n")
    assert "data: " in frame
    assert frame.endswith("\n\n")
    data_line = [ln for ln in frame.split("\n") if ln.startswith("data:")][0]
    payload = json.loads(data_line.removeprefix("data: ").strip())
    assert payload["session_id"] == "s1"
    assert payload["matched"] is True

def test_format_sse_serializes_nested_sources():
    frame = format_sse("token", {"content": "你好"})
    data_line = [ln for ln in frame.split("\n") if ln.startswith("data:")][0]
    assert json.loads(data_line.removeprefix("data: ").strip()) == {"content": "你好"}
