from datetime import datetime, timezone

from app.schemas.chat_query import SourceItem
from app.schemas.session import ChatMessage, SessionRecord, SessionSummary


def test_session_record_requires_user_id():
    record = SessionRecord(
        session_id="s1",
        user_id="user-a",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert record.user_id == "user-a"
    assert record.title == ""


def test_assistant_message_carries_sources():
    msg = ChatMessage(
        role="assistant",
        content="回复",
        sources=[SourceItem(source_title="HJ 828-2017")],
    )
    assert msg.sources[0].source_title == "HJ 828-2017"


def test_session_summary_preview():
    summary = SessionSummary(
        session_id="s1",
        title="COD咨询",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        preview="化学需氧量…",
        message_count=2,
    )
    assert summary.message_count == 2
