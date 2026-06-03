from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.exceptions import LLMServiceError
from app.schemas.session import SessionRecord

SUMMARY_SYSTEM = (
    "你是会话摘要助手。只归纳用户问过什么、助手已确认的事实。"
    "不要编造标准号。输出简短中文段落。"
)


class ContextCompressor:
    def __init__(
        self,
        summarizer: BaseChatModel,
        max_recent_messages: int = 6,
        char_threshold: int = 6000,
    ) -> None:
        self._summarizer = summarizer
        self._max_recent = max_recent_messages
        self._char_threshold = char_threshold

    def _estimate_chars(self, record: SessionRecord) -> int:
        total = len(record.summary)
        for message in record.messages:
            total += len(message.content)
        return total

    def _messages_to_summarize(self, record: SessionRecord) -> list:
        if len(record.messages) > self._max_recent:
            return record.messages[: -self._max_recent]
        if self._estimate_chars(record) > self._char_threshold and len(record.messages) > 1:
            keep = min(2, len(record.messages))
            return record.messages[:-keep]
        return []

    async def maybe_compress(self, record: SessionRecord) -> None:
        if (
            len(record.messages) <= self._max_recent
            and self._estimate_chars(record) <= self._char_threshold
        ):
            return

        to_summarize = self._messages_to_summarize(record)
        if not to_summarize:
            return

        blob = "\n".join(f"{m.role}: {m.content}" for m in to_summarize)
        prior = record.summary or "（无）"
        try:
            resp = await self._summarizer.ainvoke(
                [
                    SystemMessage(content=SUMMARY_SYSTEM),
                    HumanMessage(content=f"已有摘要：{prior}\n\n待摘要对话：\n{blob}"),
                ]
            )
        except Exception as exc:
            raise LLMServiceError("大模型服务调用失败，请稍后重试") from exc
        content = resp.content
        record.summary = content if isinstance(content, str) else str(content)
        record.messages = record.messages[len(to_summarize) :]
        if len(record.messages) > self._max_recent:
            record.messages = record.messages[-self._max_recent :]
