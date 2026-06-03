import json
from typing import Any

def format_sse(event: str, data: dict[str, Any]) -> str:
    """Format one Server-Sent Event frame (event + data + blank line)."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
