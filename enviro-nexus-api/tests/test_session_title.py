from app.llm.prompts import TITLE_SYSTEM_PROMPT, build_title_input, fallback_title


def test_build_title_input():
    text = build_title_input("COD怎么测", "采用 HJ 828-2017")
    assert "COD" in text


def test_fallback_title_truncates():
    assert len(fallback_title("a" * 100)) <= 30


def test_title_system_prompt_exists():
    assert "标题" in TITLE_SYSTEM_PROMPT
