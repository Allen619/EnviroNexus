from datetime import datetime, timezone

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.schemas.session import ChatMessage, SessionRecord
from app.services.context_compressor import ContextCompressor


@pytest.mark.asyncio
async def test_compress_moves_old_messages_into_summary():
    summarizer = FakeListChatModel(responses=["用户问过COD"])
    compressor = ContextCompressor(
        summarizer=summarizer,
        max_recent_messages=2,
        char_threshold=10,
    )
    record = SessionRecord(
        session_id="s1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        summary="",
        messages=[
            ChatMessage(role="user", content="old1"),
            ChatMessage(role="assistant", content="old2"),
            ChatMessage(role="user", content="recent"),
        ],
    )
    await compressor.maybe_compress(record)
    assert record.summary != ""
    assert len(record.messages) <= 2


@pytest.mark.asyncio
async def test_compress_when_over_char_threshold_with_few_messages():
    summarizer = FakeListChatModel(responses=["长对话摘要"])
    compressor = ContextCompressor(
        summarizer=summarizer,
        max_recent_messages=6,
        char_threshold=50,
    )
    long_text = "x" * 40
    record = SessionRecord(
        session_id="s2",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        summary="",
        messages=[
            ChatMessage(role="user", content=long_text),
            ChatMessage(role="assistant", content=long_text),
            ChatMessage(role="user", content="recent"),
        ],
    )
    await compressor.maybe_compress(record)
    assert record.summary != ""
    assert len(record.messages) < 3
