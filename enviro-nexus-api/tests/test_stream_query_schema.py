from app.schemas.stream_query import StreamDoneEvent, StreamMetaEvent, StreamTokenEvent


def test_stream_meta_event_fields():
    evt = StreamMetaEvent(
        session_id="s1",
        matched=True,
        factor="化学需氧量",
        matched_alias="COD",
        card_id="card_1",
        sources=[],
        code="OK",
    )
    assert evt.code == "OK"


def test_stream_token_event():
    assert StreamTokenEvent(content="片段").content == "片段"


def test_stream_done_event():
    evt = StreamDoneEvent(session_id="s1", reply="完整回复")
    assert evt.reply == "完整回复"
