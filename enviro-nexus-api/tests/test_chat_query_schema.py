from app.schemas.chat_query import FactorQueryRequest


def test_factor_query_request_does_not_require_factor_name():
    body = FactorQueryRequest(query="  pH 怎么测？  ", session_id="s1")

    assert body.model_dump() == {
        "query": "pH 怎么测？",
        "session_id": "s1",
    }
