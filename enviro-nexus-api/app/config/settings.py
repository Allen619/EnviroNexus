from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """应用配置，支持环境变量和 .env 文件覆盖。"""

    app_name: str = "enviro-nexus-api"
    app_version: str = "0.1.0"
    debug: bool = False

    # 知识服务配置
    knowledge_service_base_url: str = "http://localhost:8000"
    knowledge_service_timeout: float = 10.0

    # 日志配置
    log_level: str = "INFO"

    # MiniMax / LLM
    minimax_api_key: str = ""
    openai_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "MiniMax-M3"
    minimax_timeout: float = 60.0

    # Session
    session_store: str = "memory"  # memory | redis
    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 86400
    max_recent_turns: int = 6
    compress_char_threshold: int = 6000

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
