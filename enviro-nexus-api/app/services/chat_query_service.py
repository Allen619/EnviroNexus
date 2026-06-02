import logging
import uuid
from datetime import datetime, timezone

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.clients.knowledge_client import KnowledgeClient
from app.core.exceptions import KnowledgeServiceError, LLMServiceError
from app.llm.prompts import NOT_MATCHED_REPLY_FALLBACK, REPLY_SYSTEM_PROMPT, build_knowledge_block
from app.schemas.chat_query import FactorQueryData, FactorQueryResponse, SourceItem
from app.schemas.knowledge import KnowledgeFactorQueryPayload
from app.schemas.session import ChatMessage, SessionRecord
from app.services.context_compressor import ContextCompressor
from app.services.session_store import SessionStore

logger = logging.getLogger(__name__)

SESSION_EXPIRED_WARNING = "会话已过期，已开启新会话。"
FACTOR_NOT_FOUND_MESSAGE = "当前知识库暂未收录该检测因子"


class ChatQueryService:
    def __init__(
        self,
        knowledge_client: KnowledgeClient,
        session_store: SessionStore,
        chat_model: BaseChatModel,
        summarizer: BaseChatModel,
        max_recent_messages: int = 6,
        char_threshold: int = 6000,
    ) -> None:
        self._knowledge = knowledge_client
        self._store = session_store
        self._compressor = ContextCompressor(summarizer, max_recent_messages, char_threshold)
        self._chat = chat_model

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

    async def _resolve_session(
        self, session_id: str | None
    ) -> tuple[SessionRecord, list[str]]:
        warnings: list[str] = []
        record: SessionRecord | None = None

        if session_id:
            record = await self._store.get(session_id)
            if record is None:
                warnings.append(SESSION_EXPIRED_WARNING)

        now = datetime.now(timezone.utc)
        if record is None:
            record = SessionRecord(session_id=str(uuid.uuid4()), created_at=now, updated_at=now)
        return record, warnings

    async def query(
        self,
        query: str,
        request_id: str | None,
        session_id: str | None,
    ) -> FactorQueryResponse:
        record, warnings = await self._resolve_session(session_id)
        await self._compressor.maybe_compress(record)

        try:
            payload = await self._knowledge.query_factor(query)
        except (httpx.HTTPError, ValueError):
            logger.exception("knowledge query failed: query=%s", query)
            raise KnowledgeServiceError("知识服务调用失败，请稍后重试")

        knowledge_block = build_knowledge_block(payload)
        history = "\n".join(f"{m.role}: {m.content}" for m in record.messages)
        summary_part = f"【会话摘要】\n{record.summary}\n" if record.summary else ""

        if not payload.matched:
            reply = NOT_MATCHED_REPLY_FALLBACK
            code = "FACTOR_NOT_FOUND"
            message = FACTOR_NOT_FOUND_MESSAGE
        else:
            try:
                resp = await self._chat.ainvoke(
                    [
                        SystemMessage(content=REPLY_SYSTEM_PROMPT),
                        HumanMessage(
                            content=(
                                f"{summary_part}【最近对话】\n{history}\n\n"
                                f"{knowledge_block}\n\n【用户问题】\n{query}"
                            )
                        ),
                    ]
                )
                content = resp.content
                reply = content if isinstance(content, str) else str(content)
            except Exception:
                logger.exception("llm invoke failed")
                raise LLMServiceError("大模型服务调用失败，请稍后重试")
            code = "OK"
            message = "查询成功"

        record.messages.append(ChatMessage(role="user", content=query))
        record.messages.append(ChatMessage(role="assistant", content=reply))
        record.updated_at = datetime.now(timezone.utc)
        await self._store.save(record)

        return FactorQueryResponse(
            success=True,
            code=code,
            message=message,
            request_id=request_id,
            data=FactorQueryData(
                session_id=record.session_id,
                matched=payload.matched,
                reply=reply,
                factor=payload.factor,
                matched_alias=payload.matched_alias,
                card_id=payload.card_id,
                sources=self._map_sources(payload),
                warnings=warnings,
            ),
            timestamp=datetime.now(timezone.utc),
        )
