import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.clients.knowledge_client import KnowledgeClient
from app.core.api_message import (
    KNOWLEDGE_QUERY_NOT_MATCHED_REPLY,
    QUERY_REWRITE_SYSTEM_PROMPT,
)
from app.core.exceptions import KnowledgeServiceError, LLMServiceError, SessionNotFoundError
from app.llm.prompts import (
    NOT_MATCHED_REPLY_FALLBACK,
    REPLY_SYSTEM_PROMPT,
    TITLE_SYSTEM_PROMPT,
    build_knowledge_block,
    build_title_input,
    fallback_title,
)
from app.schemas.chat_query import (
    FactorQueryData,
    FactorQueryResponse,
    QueryRewriteDecision,
    SourceItem,
)
from app.schemas.knowledge import KnowledgeFactorQueryPayload
from app.schemas.session import ChatMessage, SessionRecord
from app.schemas.stream_query import StreamMetaEvent
from app.services.context_compressor import ContextCompressor
from app.services.session_store import SessionStore
from app.utils.sse import format_sse

logger = logging.getLogger(__name__)

FACTOR_NOT_FOUND_MESSAGE = "当前知识库暂未收录该检测因子"


@dataclass
class TurnContext:
    record: SessionRecord
    payload: KnowledgeFactorQueryPayload
    sources: list[SourceItem]
    llm_messages: list[SystemMessage | HumanMessage]
    query: str
    fallback_reply: str | None = None


class ChatQueryService:
    def __init__(
        self,
        knowledge_client: KnowledgeClient,
        session_store: SessionStore,
        chat_model: BaseChatModel,
        summarizer: BaseChatModel,
        rewrite_model: BaseChatModel | None = None,
        max_recent_messages: int = 6,
        char_threshold: int = 6000,
    ) -> None:
        self._knowledge = knowledge_client
        self._store = session_store
        self._compressor = ContextCompressor(summarizer, max_recent_messages, char_threshold)
        self._chat = chat_model
        self._summarizer = summarizer
        self._rewrite = rewrite_model

    def _map_sources(self, payload: KnowledgeFactorQueryPayload) -> list[SourceItem]:
        if not payload.answer:
            return []
        return [
            SourceItem(
                evidence_id=e.evidence_id,
                source_title=e.source_title,
                section=e.section,
                summary=e.summary,
                field_path=e.field_path,
            )
            for e in payload.answer.evidence_refs
        ]

    async def _load_session(self, session_id: str, user_id: str) -> SessionRecord:
        record = await self._store.get(session_id)
        if record is None or record.user_id != user_id:
            raise SessionNotFoundError()
        return record

    async def _maybe_generate_title(self, record: SessionRecord) -> None:
        if record.title or len(record.messages) != 2:
            return
        user_msg = record.messages[0].content
        assistant_msg = record.messages[1].content
        try:
            resp = await self._summarizer.ainvoke(
                [
                    SystemMessage(content=TITLE_SYSTEM_PROMPT),
                    HumanMessage(content=build_title_input(user_msg, assistant_msg)),
                ]
            )
            content = resp.content
            title = content if isinstance(content, str) else str(content)
            record.title = title.strip()[:20]
        except Exception:
            logger.warning("title generation failed for session=%s", record.session_id)
            record.title = fallback_title(user_msg)

    def _build_llm_messages(
        self,
        record: SessionRecord,
        payload: KnowledgeFactorQueryPayload,
        query: str,
    ) -> list[SystemMessage | HumanMessage]:
        knowledge_block = build_knowledge_block(payload)
        history = "\n".join(f"{m.role}: {m.content}" for m in record.messages)
        summary_part = f"【会话摘要】\n{record.summary}\n" if record.summary else ""
        return [
            SystemMessage(content=REPLY_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{summary_part}【最近对话】\n{history}\n\n"
                    f"{knowledge_block}\n\n【用户问题】\n{query}"
                )
            ),
        ]

    def _parse_rewrite_decision(self, raw: str) -> QueryRewriteDecision | None:
        try:
            return QueryRewriteDecision.model_validate_json(raw)
        except ValidationError:
            pass

        decoder = json.JSONDecoder()
        for index, char in enumerate(raw):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(raw[index:])
            except json.JSONDecodeError:
                continue
            try:
                return QueryRewriteDecision.model_validate(candidate)
            except ValidationError:
                continue
        return None

    async def _rewrite_query(
        self,
        query: str,
        fallback_factor_name: str | None,
    ) -> QueryRewriteDecision:
        if self._rewrite is None:
            return QueryRewriteDecision(
                should_query_knowledge=True,
                known_supported_factor=bool(fallback_factor_name),
                rewritten_query=query,
                factor_name=fallback_factor_name,
                confidence=1 if fallback_factor_name else 0,
            )

        try:
            resp = await self._rewrite.ainvoke(
                [
                    SystemMessage(content=QUERY_REWRITE_SYSTEM_PROMPT),
                    HumanMessage(content=query),
                ]
            )
        except Exception:
            logger.exception("query rewrite failed")
            raise LLMServiceError("大模型服务调用失败，请稍后重试")

        content = resp.content
        raw = content if isinstance(content, str) else str(content)
        rewrite = self._parse_rewrite_decision(raw)
        if rewrite is None:
            logger.warning("query rewrite returned invalid json: %s", raw)
            return QueryRewriteDecision(
                should_query_knowledge=False,
                known_supported_factor=False,
                rewritten_query="",
                factor_name=None,
                confidence=0,
            )
        return rewrite

    async def _prepare_turn(
        self,
        query: str,
        session_id: str,
        user_id: str,
        factor_name: str | None = None,
    ) -> TurnContext:
        record = await self._load_session(session_id, user_id)
        await self._compressor.maybe_compress(record)
        rewrite = await self._rewrite_query(query, factor_name)
        rewritten_query = rewrite.rewritten_query.strip() or query
        rewritten_factor = rewrite.factor_name.strip() if rewrite.factor_name else None

        if not rewrite.should_query_knowledge:
            return TurnContext(
                record=record,
                payload=KnowledgeFactorQueryPayload(
                    matched=False,
                    factor=rewritten_factor,
                    warnings=["QUERY_REWRITE_NOT_MATCHED"],
                ),
                sources=[],
                llm_messages=[],
                query=query,
                fallback_reply=KNOWLEDGE_QUERY_NOT_MATCHED_REPLY,
            )

        try:
            payload = await self._knowledge.query_factor(rewritten_query)
        except (httpx.HTTPError, ValueError):
            logger.exception("knowledge query failed: query=%s", query)
            raise KnowledgeServiceError("知识服务调用失败，请稍后重试")
        sources = self._map_sources(payload)
        llm_messages = self._build_llm_messages(record, payload, query)
        return TurnContext(
            record=record,
            payload=payload,
            sources=sources,
            llm_messages=llm_messages,
            query=query,
        )

    def _build_meta_payload(self, ctx: TurnContext) -> dict:
        code = "OK" if ctx.payload.matched else "FACTOR_NOT_FOUND"
        event = StreamMetaEvent(
            session_id=ctx.record.session_id,
            matched=ctx.payload.matched,
            factor=ctx.payload.factor,
            matched_alias=ctx.payload.matched_alias,
            card_id=ctx.payload.card_id,
            sources=ctx.sources,
            code=code,
        )
        return event.model_dump(mode="json")

    async def _collect_llm_reply(
        self, messages: list[SystemMessage | HumanMessage]
    ) -> str:
        try:
            resp = await self._chat.ainvoke(messages)
        except Exception:
            logger.exception("llm invoke failed")
            raise LLMServiceError("大模型服务调用失败，请稍后重试")
        content = resp.content
        return content if isinstance(content, str) else str(content)

    async def _stream_llm_tokens(
        self, messages: list[SystemMessage | HumanMessage]
    ):
        async for chunk in self._chat.astream(messages):
            content = chunk.content
            if content:
                text = content if isinstance(content, str) else str(content)
                yield text

    async def _finalize_turn(self, ctx: TurnContext, reply: str) -> None:
        ctx.record.messages.append(ChatMessage(role="user", content=ctx.query))
        ctx.record.messages.append(
            ChatMessage(role="assistant", content=reply, sources=ctx.sources)
        )
        ctx.record.updated_at = datetime.now(timezone.utc)
        await self._maybe_generate_title(ctx.record)
        await self._store.save(ctx.record)

    async def query(
        self,
        query: str,
        request_id: str | None,
        session_id: str,
        user_id: str,
        factor_name: str | None = None,
    ) -> FactorQueryResponse:
        ctx = await self._prepare_turn(query, session_id, user_id, factor_name)

        if not ctx.payload.matched:
            reply = ctx.fallback_reply or NOT_MATCHED_REPLY_FALLBACK
            code = "FACTOR_NOT_FOUND"
            message = ctx.fallback_reply or FACTOR_NOT_FOUND_MESSAGE
        else:
            reply = await self._collect_llm_reply(ctx.llm_messages)
            code = "OK"
            message = "查询成功"

        await self._finalize_turn(ctx, reply)

        return FactorQueryResponse(
            success=True,
            code=code,
            message=message,
            request_id=request_id,
            data=FactorQueryData(
                session_id=ctx.record.session_id,
                matched=ctx.payload.matched,
                reply=reply,
                factor=ctx.payload.factor,
                matched_alias=ctx.payload.matched_alias,
                card_id=ctx.payload.card_id,
                sources=ctx.sources,
                warnings=ctx.payload.warnings,
            ),
            timestamp=datetime.now(timezone.utc),
        )

    async def query_stream(
        self,
        query: str,
        session_id: str,
        user_id: str,
        factor_name: str | None = None,
    ):
        ctx = await self._prepare_turn(query, session_id, user_id, factor_name)
        async for frame in self._stream_prepared_turn(ctx):
            yield frame

    async def open_query_stream(
        self,
        query: str,
        session_id: str,
        user_id: str,
        factor_name: str | None = None,
    ):
        ctx = await self._prepare_turn(query, session_id, user_id, factor_name)
        return self._stream_prepared_turn(ctx)

    async def _stream_prepared_turn(self, ctx: TurnContext):
        from app.schemas.stream_query import StreamDoneEvent, StreamErrorEvent, StreamTokenEvent

        yield format_sse("meta", self._build_meta_payload(ctx))

        if not ctx.payload.matched:
            reply = ctx.fallback_reply or NOT_MATCHED_REPLY_FALLBACK
            yield format_sse("token", StreamTokenEvent(content=reply).model_dump(mode="json"))
        else:
            reply_parts: list[str] = []
            try:
                async for chunk in self._stream_llm_tokens(ctx.llm_messages):
                    reply_parts.append(chunk)
                    yield format_sse(
                        "token", StreamTokenEvent(content=chunk).model_dump(mode="json")
                    )
            except Exception:
                logger.exception("llm stream failed")
                yield format_sse(
                    "error",
                    StreamErrorEvent(
                        code="LLM_SERVICE_ERROR",
                        message="大模型服务调用失败，请稍后重试",
                    ).model_dump(mode="json"),
                )
                return
            reply = "".join(reply_parts)

        await self._finalize_turn(ctx, reply)
        yield format_sse(
            "done",
            StreamDoneEvent(
                session_id=ctx.record.session_id,
                reply=reply,
            ).model_dump(mode="json"),
        )
