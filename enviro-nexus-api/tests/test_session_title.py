from app.llm.prompts import (
    TITLE_SYSTEM_PROMPT,
    build_title_input,
    clean_title_output,
    fallback_title,
)


def test_build_title_input():
    text = build_title_input("COD怎么测", "采用 HJ 828-2017")
    assert "COD" in text


def test_build_title_input_uses_only_first_user_question():
    text = build_title_input("PH怎么测试", "与知识库不匹配，请重试")
    assert "PH怎么测试" in text
    assert "与知识库不匹配" not in text


def test_fallback_title_truncates():
    assert len(fallback_title("a" * 100)) <= 30


def test_title_system_prompt_exists():
    assert "标题" in TITLE_SYSTEM_PROMPT


def test_clean_title_output_removes_think_block_and_uses_body():
    assert (
        clean_title_output("<think>分析首轮问答</think>COD测定咨询", "COD怎么测")
        == "COD测定咨询"
    )


def test_clean_title_output_falls_back_for_malformed_reasoning():
    assert clean_title_output("<think>\nThe user is asking", "COD怎么测") == "COD怎么测"


def test_clean_title_output_falls_back_for_leftover_think_tag():
    assert clean_title_output("COD </think", "COD怎么测") == "COD怎么测"


def test_clean_title_output_falls_back_for_stray_complete_think_tag():
    assert clean_title_output("COD </think> 咨询", "COD怎么测") == "COD怎么测"


def test_clean_title_output_falls_back_for_stray_tag_after_think_block():
    assert clean_title_output("<think>分析</think>COD</think>", "COD怎么测") == "COD怎么测"


def test_clean_title_output_trims_wrappers_and_punctuation():
    assert clean_title_output("“COD测定咨询。”", "COD怎么测") == "COD测定咨询"
