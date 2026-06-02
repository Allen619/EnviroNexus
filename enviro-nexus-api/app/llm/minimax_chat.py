from langchain_openai import ChatOpenAI

from app.config.settings import Settings


def get_chat_model(settings: Settings, *, temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.minimax_model,
        api_key=settings.minimax_api_key or None,
        base_url=settings.minimax_base_url,
        temperature=temperature,
        timeout=settings.minimax_timeout,
    )


def get_summarizer_model(settings: Settings) -> ChatOpenAI:
    return get_chat_model(settings, temperature=0.0)
