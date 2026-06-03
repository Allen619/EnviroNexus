from langchain_openai import ChatOpenAI

from app.config.settings import Settings


def _resolve_api_key(settings: Settings) -> str:
    api_key = (settings.minimax_api_key or settings.openai_api_key).strip()
    if not api_key:
        raise RuntimeError(
            "缺少大模型 API Key。请在环境变量或 .env 中设置 MINIMAX_API_KEY（推荐）"
            "或 OPENAI_API_KEY。"
        )
    return api_key


def get_chat_model(settings: Settings, *, temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.minimax_model,
        api_key=_resolve_api_key(settings),
        base_url=settings.minimax_base_url,
        temperature=temperature,
        timeout=settings.minimax_timeout,
    )


def get_summarizer_model(settings: Settings) -> ChatOpenAI:
    return get_chat_model(settings, temperature=0.0)
