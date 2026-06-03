import re
import unicodedata


QUESTION_NOISE_PHRASES = (
    "用什么方法",
    "用哪个标准",
    "用什么标准",
    "怎么测",
    "标准",
    "检测",
    "测定",
    "方法",
)

PUNCTUATION_PATTERN = re.compile(r"[?？!！,，。；;:：、/\\|()[\]{}<>《》\"'“”‘’`~@#$%^&*_+=-]+")
SPACE_PATTERN = re.compile(r"\s+")


def normalize_query(text: str) -> str:
    return _normalize(text, remove_query_noise=True)


def normalize_alias(text: str) -> str:
    return _normalize(text, remove_query_noise=False)


def _normalize(text: str, *, remove_query_noise: bool) -> str:
    normalized = unicodedata.normalize("NFKC", text.strip()).lower()
    normalized = re.sub(r"ph\s*值", "ph", normalized)

    if remove_query_noise:
        for phrase in QUESTION_NOISE_PHRASES:
            normalized = normalized.replace(phrase, "")

    normalized = PUNCTUATION_PATTERN.sub(" ", normalized)
    normalized = SPACE_PATTERN.sub(" ", normalized).strip()
    return normalized
