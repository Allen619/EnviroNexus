# Session Title Cleaning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent model reasoning text such as `<think>` from being stored as a session title while preserving usable model-generated titles before falling back to the first user question.

**Architecture:** Add a focused pure function in `app/llm/prompts.py` to normalize and validate raw title model output. Keep `ChatQueryService` responsible for deciding when to generate a title, but delegate output cleaning to the prompt utility module before saving the session.

**Tech Stack:** Python 3.12, FastAPI service layer, LangChain fake chat models in tests, pytest with pytest-asyncio.

---

## File Structure

- Modify `app/llm/prompts.py`: add `clean_title_output(raw_title, first_user_message)` and small private helpers/constants for title cleanup.
- Modify `app/services/chat_query_service.py`: import `clean_title_output` and use it in `_maybe_generate_title`.
- Modify `tests/test_session_title.py`: add pure unit tests for title cleanup behavior.
- Modify `tests/test_chat_query_service.py`: add async service tests proving the cleaned title is persisted.

---

### Task 1: Add Pure Function Tests

**Files:**
- Modify: `tests/test_session_title.py`
- Test: `tests/test_session_title.py`

- [ ] **Step 1: Add failing tests for title cleanup**

Replace the import at the top of `tests/test_session_title.py` with:

```python
from app.llm.prompts import (
    TITLE_SYSTEM_PROMPT,
    build_title_input,
    clean_title_output,
    fallback_title,
)
```

Append these tests to `tests/test_session_title.py`:

```python
def test_clean_title_output_removes_think_block_and_uses_body():
    assert (
        clean_title_output("<think>分析首轮问答</think>COD测定咨询", "COD怎么测")
        == "COD测定咨询"
    )


def test_clean_title_output_falls_back_for_malformed_reasoning():
    assert clean_title_output("<think>\nThe user is asking", "COD怎么测") == "COD怎么测"


def test_clean_title_output_trims_wrappers_and_punctuation():
    assert clean_title_output("“COD测定咨询。”", "COD怎么测") == "COD测定咨询"
```

- [ ] **Step 2: Run the new pure function tests and verify they fail**

Run:

```powershell
uv run pytest tests/test_session_title.py -v
```

Expected: FAIL during collection with an import error for `clean_title_output`, because the function does not exist yet.

---

### Task 2: Implement Title Cleanup Utility

**Files:**
- Modify: `app/llm/prompts.py`
- Test: `tests/test_session_title.py`

- [ ] **Step 1: Add regex import**

At the top of `app/llm/prompts.py`, before the existing schema import, add:

```python
import re
```

- [ ] **Step 2: Add title cleanup constants and helpers**

Insert this block after `TITLE_SYSTEM_PROMPT` and before `build_title_input`:

```python
TITLE_MAX_LEN = 20
_TITLE_WRAPPER_CHARS = " \t\r\n\"'“”‘’《》「」『』:：-—"
_TITLE_TRAILING_PUNCT = "。.!！?？,，;；"
_THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_TAG_RE = re.compile(r"</?think\b[^>]*>", re.IGNORECASE)
_REASONING_PREFIXES = (
    "the user",
    "user ",
    "用户问的是",
    "用户询问",
    "用户想",
    "用户问",
    "助手",
)


def _is_displayable_title(text: str) -> bool:
    if not text:
        return False

    lowered = text.lower().lstrip()
    if lowered.startswith(("<think", "</think")):
        return False
    return not any(lowered.startswith(prefix) for prefix in _REASONING_PREFIXES)
```

- [ ] **Step 3: Add `clean_title_output`**

Insert this function after `_is_displayable_title` and before `build_title_input`:

```python
def clean_title_output(raw_title: object, first_user_message: str) -> str:
    original = raw_title if isinstance(raw_title, str) else str(raw_title)
    has_open_think = bool(re.search(r"<think\b", original, re.IGNORECASE))
    has_close_think = bool(re.search(r"</think>", original, re.IGNORECASE))

    if has_open_think and not has_close_think:
        return fallback_title(first_user_message)

    text = _THINK_BLOCK_RE.sub("", original).strip()
    text = _THINK_TAG_RE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(_TITLE_WRAPPER_CHARS)
    text = text.rstrip(_TITLE_TRAILING_PUNCT).strip(_TITLE_WRAPPER_CHARS)

    if not _is_displayable_title(text):
        return fallback_title(first_user_message)
    return text[:TITLE_MAX_LEN]
```

- [ ] **Step 4: Confirm `fallback_title` keeps the existing fallback contract**

Keep the existing `fallback_title` implementation as:

```python
def fallback_title(first_user_message: str) -> str:
    text = first_user_message.strip()
    if len(text) <= 30:
        return text
    return text[:29] + "…"
```

This keeps the existing 30-character fallback contract unchanged. `TITLE_MAX_LEN` applies only to model-generated titles.

- [ ] **Step 5: Run pure function tests and verify they pass**

Run:

```powershell
uv run pytest tests/test_session_title.py -v
```

Expected: PASS for all tests in `tests/test_session_title.py`.

- [ ] **Step 6: Commit pure utility change**

Run:

```powershell
git add app/llm/prompts.py tests/test_session_title.py
git commit -m "feat: clean generated session titles"
```

Expected: commit succeeds with only `app/llm/prompts.py` and `tests/test_session_title.py` staged.

---

### Task 3: Add Service Persistence Tests

**Files:**
- Modify: `tests/test_chat_query_service.py`
- Test: `tests/test_chat_query_service.py`

- [ ] **Step 1: Add failing service tests for persisted titles**

Append these tests after `test_query_generates_title_after_first_turn` in `tests/test_chat_query_service.py`:

```python
@pytest.mark.asyncio
async def test_query_persists_cleaned_title_after_first_turn():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["采用 HJ 828-2017 测定。"]),
        summarizer=FakeListChatModel(
            responses=["<think>分析首轮问答</think>COD测定咨询"]
        ),
        char_threshold=100000,
    )

    await svc.query(
        query="COD怎么测",
        factor_name="化学需氧量",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )

    loaded = await store.get(session_id)
    assert loaded is not None
    assert loaded.title == "COD测定咨询"


@pytest.mark.asyncio
async def test_query_title_fallback_when_generated_title_is_reasoning_residue():
    store = InMemorySessionStore()
    user_id = "user-1"
    session_id = await _create_session(store, user_id)
    knowledge = AsyncMock()
    knowledge.query_factor.return_value = _matched_payload()
    query_text = "COD怎么测"
    svc = ChatQueryService(
        knowledge_client=knowledge,
        session_store=store,
        chat_model=FakeListChatModel(responses=["采用 HJ 828-2017 测定。"]),
        summarizer=FakeListChatModel(
            responses=["<think>\nThe user is asking how to measure COD"]
        ),
        char_threshold=100000,
    )

    await svc.query(
        query=query_text,
        factor_name="化学需氧量",
        request_id=None,
        session_id=session_id,
        user_id=user_id,
    )

    loaded = await store.get(session_id)
    assert loaded is not None
    assert loaded.title == fallback_title(query_text)
```

- [ ] **Step 2: Run the new service tests and verify they fail**

Run:

```powershell
uv run pytest tests/test_chat_query_service.py::test_query_persists_cleaned_title_after_first_turn tests/test_chat_query_service.py::test_query_title_fallback_when_generated_title_is_reasoning_residue -v
```

Expected: FAIL because `ChatQueryService._maybe_generate_title` still stores `title.strip()[:20]` from the raw model output.

---

### Task 4: Wire Cleanup Into ChatQueryService

**Files:**
- Modify: `app/services/chat_query_service.py`
- Test: `tests/test_chat_query_service.py`

- [ ] **Step 1: Import `clean_title_output`**

In the import block from `app.llm.prompts`, add `clean_title_output`:

```python
from app.llm.prompts import (
    NOT_MATCHED_REPLY_FALLBACK,
    REPLY_SYSTEM_PROMPT,
    TITLE_SYSTEM_PROMPT,
    build_knowledge_block,
    build_title_input,
    clean_title_output,
    fallback_title,
)
```

- [ ] **Step 2: Use the cleanup function before saving the title**

Inside `_maybe_generate_title`, replace:

```python
            record.title = title.strip()[:20]
```

with:

```python
            record.title = clean_title_output(title, user_msg)
```

- [ ] **Step 3: Run the targeted service tests and verify they pass**

Run:

```powershell
uv run pytest tests/test_chat_query_service.py::test_query_generates_title_after_first_turn tests/test_chat_query_service.py::test_query_persists_cleaned_title_after_first_turn tests/test_chat_query_service.py::test_query_title_fallback_when_generated_title_is_reasoning_residue tests/test_chat_query_service.py::test_query_title_fallback_on_summarizer_failure -v
```

Expected: PASS for all four title-related service tests.

- [ ] **Step 4: Run combined title regression**

Run:

```powershell
uv run pytest tests/test_session_title.py tests/test_chat_query_service.py -v
```

Expected: PASS for both files.

- [ ] **Step 5: Commit service wiring**

Run:

```powershell
git add app/services/chat_query_service.py tests/test_chat_query_service.py
git commit -m "fix: clean session titles before saving"
```

Expected: commit succeeds with only `app/services/chat_query_service.py` and `tests/test_chat_query_service.py` staged.

---

### Task 5: Final Regression

**Files:**
- Verify: repository test suite

- [ ] **Step 1: Run full tests**

Run:

```powershell
uv run pytest -v
```

Expected: PASS for the full test suite.

- [ ] **Step 2: Check working tree**

Run:

```powershell
git status --short
```

Expected: no unstaged or untracked implementation changes. The plan file may remain uncommitted if the execution process does not commit planning artifacts.

- [ ] **Step 3: Summarize behavior**

Report these verified outcomes:

```text
- `<think>...</think>COD测定咨询` is saved as `COD测定咨询`.
- malformed reasoning output such as `<think>\nThe user is...` falls back to the first user question.
- existing summarizer exceptions still fall back through the original exception path.
```

---

## Self-Review

Spec coverage:

- Model-generated title remains the first priority: Task 2 returns cleaned model output when displayable.
- User-question truncation remains the fallback: Task 2 and Task 4 use `fallback_title` for invalid output and existing exceptions.
- `<think>` reasoning leakage is covered: Task 1 and Task 3 include pure and service-level tests.
- API, storage, preview, prompt protocol, and extra LLM calls stay unchanged: no task touches those areas.

Placeholder scan:

- The plan contains concrete file paths, code snippets, commands, and expected results.
- No open-ended implementation steps are left.

Type consistency:

- `clean_title_output(raw_title: object, first_user_message: str) -> str` is imported and called with the raw title model content plus the first user message.
- `fallback_title(first_user_message: str) -> str` keeps its existing behavior and call sites.
