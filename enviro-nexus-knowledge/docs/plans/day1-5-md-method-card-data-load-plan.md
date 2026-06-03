# Day 1.5 Markdown MethodCard Data Load Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task after user approval. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear the current local PostgreSQL business data, manually extract the five markdown standards under `files/poc-files`, convert them into MethodCard seed data, import them through the existing Day 1 import service, and verify query behavior without entering Day 2.

**Architecture:** Keep the existing Day 1 runtime unchanged: `seed JSON -> MethodCard Schema -> import service -> PostgreSQL -> factor matcher -> answer_builder -> evidence_builder -> POST /api/v1/factors/query`. This task only expands seed data and adjusts tests that currently assume one pH card.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, Alembic, PostgreSQL 16 in Docker, pytest, existing deterministic factor matcher.

---

## 1. Scope

This is a Day 1.5 data-load task, not Day 2.

Allowed:

- Read the five markdown files under `files/poc-files`.
- Manually construct MethodCard seed JSON from the markdown content.
- Replace or expand existing seed files under `enviro-nexus-knowledge/data/seed`.
- Adjust tests so they validate the expanded seed dataset.
- Clear rows from Day 1 business tables before import.
- Run existing import service and API/query tests.

Not allowed:

- Do not modify `enviro-nexus-api`.
- Do not modify `enviro-nexus-web`.
- Do not add PDF parsing.
- Do not add automatic markdown extraction code unless the user explicitly asks later.
- Do not add RAG, embeddings, pgvector, or LLM answering.
- Do not change business logic unless a failing test proves the current Day 1 logic is incompatible with valid seed data.
- If evidence linkage for `answer_template` or `measurement` requires schema support, limit code changes to the existing MethodCard schema, evidence builder, answer builder, and focused tests.
- Do not delete database schema or migration state.

Database clearing means deleting rows from these business tables only:

```text
factor_aliases
method_cards
source_documents
knowledge_import_batches
```

Keep this table intact:

```text
alembic_version
```

## 2. Source Markdown Files

Use these exact files as the source of truth:

```text
D:\szy\code\my-project\enviro-nexus\files\poc-files\HJ 1287-2023 固定污染源废气 烟气黑度的测定 林格曼望远镜法.md
D:\szy\code\my-project\enviro-nexus\files\poc-files\HJ 1332-2023 固定污染源废气 总烃、甲烷和非甲烷总烃的测定 便携式气相色谱-氢火焰离子化检测器法.md
D:\szy\code\my-project\enviro-nexus\files\poc-files\HJ 1445-2026 水质 高锰酸盐指数的测定 草酸钠还原酸性滴定法.md
D:\szy\code\my-project\enviro-nexus\files\poc-files\水质 pH的测定 电极法 HJ 1147-2020.md
D:\szy\code\my-project\enviro-nexus\files\poc-files\水质 色度的测定 稀释倍数法 HJ 1182-2021.md
```

`source_documents.file_path` should point to these markdown paths as metadata. Do not require local PDF existence.

## 3. Target Cards

Create or keep exactly these five MethodCards.

### 3.1 pH

File:

```text
enviro-nexus-knowledge/data/seed/method_cards/water_ph_hj1147_2020.json
```

Identity:

```text
card_id: water_ph_hj1147_2020
category: 水质
factor: pH 值
standard_code: HJ 1147-2020
standard_name: 水质 pH 值的测定 电极法
method_name: 电极法
aliases: pH, PH, pH值, PH值, 酸碱度
```

Required evidence sections:

```text
1 适用范围
3 方法原理
6 仪器和设备
7 样品
8 分析步骤
9 结果表示
11 质量保证和质量控制
```

Notes:

- Existing pH card can be reused if it still validates.
- Update source file metadata from PDF path to markdown path if needed.

### 3.2 色度

File:

```text
enviro-nexus-knowledge/data/seed/method_cards/water_colority_hj1182_2021.json
```

Identity:

```text
card_id: water_colority_hj1182_2021
category: 水质
factor: 色度
standard_code: HJ 1182-2021
standard_name: 水质 色度的测定 稀释倍数法
method_name: 稀释倍数法
aliases: 色度, 水质色度, 颜色, 稀释倍数
```

Required evidence sections:

```text
1 适用范围
6 人员、环境和设备
7 样品
7.1 样品采集和保存
7.2 试样的制备
7.3 颜色描述
8.1 初级稀释
8.2 自然倍数稀释
8.3 目视比色
11 质量保证和质量控制
```

### 3.3 高锰酸盐指数

File:

```text
enviro-nexus-knowledge/data/seed/method_cards/water_permanganate_index_hj1445_2026.json
```

Identity:

```text
card_id: water_permanganate_index_hj1445_2026
category: 水质
factor: 高锰酸盐指数
standard_code: HJ 1445-2026
standard_name: 水质 高锰酸盐指数的测定 草酸钠还原酸性滴定法
method_name: 草酸钠还原酸性滴定法
aliases: 高锰酸盐指数, CODMn, CODmn, IMn, 耗氧量
```

Required evidence sections:

```text
1 适用范围
3 术语和定义
4 方法原理
5 干扰和消除
6 试剂和材料
8 样品
9 分析步骤
10 结果计算与表示
12 质量保证和质量控制
13 注意事项
```

Important matcher constraint:

- `CODMn` should match this card through exact normalized alias `codmn`.
- `COD 怎么测？` must still return `matched=false`.
- Do not weaken the ASCII abbreviation guard in `factor_matcher.py`.

### 3.4 烟气黑度

File:

```text
enviro-nexus-knowledge/data/seed/method_cards/gas_smoke_blackness_hj1287_2023.json
```

Identity:

```text
card_id: gas_smoke_blackness_hj1287_2023
category: 固定污染源废气
factor: 烟气黑度
standard_code: HJ 1287-2023
standard_name: 固定污染源废气 烟气黑度的测定 林格曼望远镜法
method_name: 林格曼望远镜法
aliases: 烟气黑度, 林格曼黑度, 黑度, 烟尘黑度
```

Required evidence sections:

```text
1 适用范围
4 方法原理
8.1 结果计算
8.2 结果表示
10 质量保证和质量控制
11 注意事项
附录 B 林格曼望远镜烟气黑度观测记录表
```

### 3.5 总烃、甲烷和非甲烷总烃

File:

```text
enviro-nexus-knowledge/data/seed/method_cards/gas_thc_methane_nmhc_hj1332_2023.json
```

Identity:

```text
card_id: gas_thc_methane_nmhc_hj1332_2023
category: 固定污染源废气
factor: 总烃、甲烷和非甲烷总烃
standard_code: HJ 1332-2023
standard_name: 固定污染源废气 总烃、甲烷和非甲烷总烃的测定 便携式气相色谱-氢火焰离子化检测器法
method_name: 便携式气相色谱-氢火焰离子化检测器法
aliases: 总烃, THC, 甲烷, CH4, CH₄, 非甲烷总烃, NMHC, 非甲烷烃
```

Use `identity.factors` to represent the three factors:

```text
总烃: 总烃, THC
甲烷: 甲烷, CH4, CH₄
非甲烷总烃: 非甲烷总烃, NMHC, 非甲烷烃
```

Required evidence sections:

```text
1 适用范围
4 方法原理
5 干扰和消除
6 试剂和材料
7 仪器和设备
8 样品
9 分析步骤
10 结果计算与表示
12 质量保证和质量控制
13 注意事项
```

## 4. Seed Files to Modify

Modify these existing files:

```text
enviro-nexus-knowledge/data/seed/source_documents.json
enviro-nexus-knowledge/data/seed/factor_aliases.json
enviro-nexus-knowledge/data/seed/sample_queries.json
enviro-nexus-knowledge/data/seed/method_cards/water_ph_hj1147_2020.json
```

Create these files:

```text
enviro-nexus-knowledge/data/seed/method_cards/water_colority_hj1182_2021.json
enviro-nexus-knowledge/data/seed/method_cards/water_permanganate_index_hj1445_2026.json
enviro-nexus-knowledge/data/seed/method_cards/gas_smoke_blackness_hj1287_2023.json
enviro-nexus-knowledge/data/seed/method_cards/gas_thc_methane_nmhc_hj1332_2023.json
enviro-nexus-knowledge/docs/reports/day1_5_coverage_report.md
```

`day1_5_coverage_report.md` is the data coverage and manual review report. It must record which markdown sections were used for each MethodCard, which fields remain manually summarized, which source sections need later PDF cross-checking, and the final reviewer status for each card.

Do not modify:

```text
enviro-nexus-api/
enviro-nexus-web/
```

## 5. Source Document Rows

`source_documents.json` should contain exactly five rows:

```text
doc_hj1147_2020 -> HJ 1147-2020 -> 水质 pH 值的测定 电极法
doc_hj1182_2021 -> HJ 1182-2021 -> 水质 色度的测定 稀释倍数法
doc_hj1445_2026 -> HJ 1445-2026 -> 水质 高锰酸盐指数的测定 草酸钠还原酸性滴定法
doc_hj1287_2023 -> HJ 1287-2023 -> 固定污染源废气 烟气黑度的测定 林格曼望远镜法
doc_hj1332_2023 -> HJ 1332-2023 -> 固定污染源废气 总烃、甲烷和非甲烷总烃的测定 便携式气相色谱-氢火焰离子化检测器法
```

For every row:

```text
source_type: standard
status: active
metadata.manual_extract_status: completed
metadata.source_format: markdown
metadata.derived_from: files/poc-files/<exact markdown filename>
metadata.needs_pdf_check: true
```

`metadata.derived_from` must be the exact markdown source path relative to the repository root. `source_documents.file_path` should also point to the markdown source path for Day 1.5 metadata; no PDF file existence check is allowed in this task.

## 6. Alias Seed

`factor_aliases.json` should store normalized aliases after de-duplication by `(normalized_alias, card_id)`.

Minimum required aliases:

```text
pH 值 -> ph -> water_ph_hj1147_2020
酸碱度 -> 酸碱度 -> water_ph_hj1147_2020
色度 -> 色度 -> water_colority_hj1182_2021
水质色度 -> 水质色度 -> water_colority_hj1182_2021
高锰酸盐指数 -> 高锰酸盐指数 -> water_permanganate_index_hj1445_2026
CODMn -> codmn -> water_permanganate_index_hj1445_2026
IMn -> imn -> water_permanganate_index_hj1445_2026
耗氧量 -> 耗氧量 -> water_permanganate_index_hj1445_2026
烟气黑度 -> 烟气黑度 -> gas_smoke_blackness_hj1287_2023
林格曼黑度 -> 林格曼黑度 -> gas_smoke_blackness_hj1287_2023
总烃 -> 总烃 -> gas_thc_methane_nmhc_hj1332_2023
THC -> thc -> gas_thc_methane_nmhc_hj1332_2023
甲烷 -> 甲烷 -> gas_thc_methane_nmhc_hj1332_2023
CH4 -> ch4 -> gas_thc_methane_nmhc_hj1332_2023
非甲烷总烃 -> 非甲烷总烃 -> gas_thc_methane_nmhc_hj1332_2023
NMHC -> nmhc -> gas_thc_methane_nmhc_hj1332_2023
```

Do not add a plain `COD` alias in this task.

## 7. Test Files to Modify

Modify these test files only as needed:

```text
enviro-nexus-knowledge/tests/unit/test_method_card_schema.py
enviro-nexus-knowledge/tests/unit/test_answer_builder.py
enviro-nexus-knowledge/tests/unit/test_factor_matcher.py
enviro-nexus-knowledge/tests/integration/test_seed_import.py
enviro-nexus-knowledge/tests/integration/test_factor_query_api.py
```

Expected test changes:

- Validate every `data/seed/method_cards/*.json` file with `MethodCard.model_validate`.
- Validate that `answer_template.evidence_ids`, `applicability.evidence_ids`, and `measurement.evidence_ids` are non-empty and reference existing `evidence_refs`.
- Keep pH normalizer tests unchanged.
- Keep `COD 怎么测？` unmatched tests.
- Keep `CODMn 怎么测？` matched tests.
- Add or keep `cod` vs `codmn` unit matcher protection.
- Update import integration expected counts from one card to five cards.
- Add integration query cases for `CODMn 怎么测？`, `色度怎么测？`, `烟气黑度怎么测？`, and `非甲烷总烃怎么测？`.
- Assert `sample_queries.json` uses these `expected_card_id` values exactly:

```text
pH 怎么测？ -> water_ph_hj1147_2020
水样酸碱度用什么标准？ -> water_ph_hj1147_2020
色度怎么测？ -> water_colority_hj1182_2021
CODMn 怎么测？ -> water_permanganate_index_hj1445_2026
烟气黑度怎么测？ -> gas_smoke_blackness_hj1287_2023
非甲烷总烃怎么测？ -> gas_thc_methane_nmhc_hj1332_2023
COD 怎么测？ -> null, matched=false
```

Do not modify tests to hide failures. If a test fails because the seed violates schema, fix the seed.

### 7.1 Application Files for Evidence Linkage

Only if required to enforce evidence linkage for fields that enter the answer, modify these application files:

```text
enviro-nexus-knowledge/app/schemas/method_card.py
enviro-nexus-knowledge/app/core/evidence_builder.py
enviro-nexus-knowledge/app/core/answer_builder.py
```

Expected changes:

- Add `evidence_ids: list[str] = Field(min_length=1)` to `AnswerTemplate`.
- Add `evidence_ids: list[str] = Field(min_length=1)` to `Measurement`.
- Extend MethodCard cross-field validation so `answer_template.evidence_ids` and `measurement.evidence_ids` must exist in `evidence_refs`.
- Extend `evidence_builder` so answer evidence includes evidence ids from `answer_template`, `applicability`, `measurement`, `requirements`, and `qa_qc`.
- Keep API response shape stable; the new `evidence_ids` fields are internal validation/linkage metadata and should not be exposed directly unless already part of the existing answer contract.

## 8. Task Plan

### Task 1: Pre-flight Snapshot

**Files:** no writes.

- [ ] Run current git status:

```powershell
git -c core.quotepath=false status --short
```

- [ ] Confirm PostgreSQL container is available:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
docker compose ps postgres
```

- [ ] Capture current table counts before clearing:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
docker compose exec -T postgres psql -U enviro_nexus -d enviro_nexus_knowledge -c "SELECT 'source_documents' AS table_name, count(*) FROM source_documents UNION ALL SELECT 'method_cards', count(*) FROM method_cards UNION ALL SELECT 'factor_aliases', count(*) FROM factor_aliases UNION ALL SELECT 'knowledge_import_batches', count(*) FROM knowledge_import_batches ORDER BY table_name;"
```

Expected output before clearing may vary. Record it for the final report.

### Task 2: Manually Extract Five MethodCards

**Files:**

- Modify: `enviro-nexus-knowledge/data/seed/source_documents.json`
- Modify: `enviro-nexus-knowledge/data/seed/factor_aliases.json`
- Modify: `enviro-nexus-knowledge/data/seed/sample_queries.json`
- Modify: `enviro-nexus-knowledge/data/seed/method_cards/water_ph_hj1147_2020.json`
- Create: `enviro-nexus-knowledge/data/seed/method_cards/water_colority_hj1182_2021.json`
- Create: `enviro-nexus-knowledge/data/seed/method_cards/water_permanganate_index_hj1445_2026.json`
- Create: `enviro-nexus-knowledge/data/seed/method_cards/gas_smoke_blackness_hj1287_2023.json`
- Create: `enviro-nexus-knowledge/data/seed/method_cards/gas_thc_methane_nmhc_hj1332_2023.json`
- Create: `enviro-nexus-knowledge/docs/reports/day1_5_coverage_report.md`

- [ ] For each markdown file, extract only sections needed for a MethodCard:

```text
适用范围 -> applicability.scope_summary, sample_types, exclusions, ev_scope
方法原理 -> measurement.principle, ev_principle
仪器和设备 / 人员、环境和设备 -> measurement.instrument, instrument requirement
回答摘要 -> answer_template.short_answer, answer_template.evidence_ids
样品 -> sample_collection or sample_preservation requirement
分析步骤 -> analysis_step requirement
结果计算与表示 / 结果表示 -> result_expression requirement
干扰和消除 -> interference requirement when the section exists
质量保证和质量控制 -> qa_qc
注意事项 / 废物处理 -> safety_note or other requirement when useful
```

- [ ] Every MethodCard must satisfy:

```text
schema_version = method_card.v0.1
card_id matches ^[a-z0-9_]+$
card_version = 1
requirements length >= 3
qa_qc length >= 1
evidence_refs length >= 5
governance.review_status = approved
governance.answer_visibility = enabled
identity.aliases covers every identity.factors[].aliases entry
answer_template.evidence_ids length >= 1
applicability.evidence_ids length >= 1
measurement.evidence_ids length >= 1
every answer_template evidence_id exists in evidence_refs
every applicability evidence_id exists in evidence_refs
every measurement evidence_id exists in evidence_refs
every requirement evidence_id exists in evidence_refs
every qa_qc evidence_id exists in evidence_refs
```

Current Day 1 schema already validates `applicability.evidence_ids`, `requirements[].evidence_ids`, and `qa_qc[].evidence_ids`. Day 1.5 must also add evidence linkage for `answer_template` and `measurement` before these fields enter API answers.

- [ ] Keep evidence summaries concise and tied to a section, not a full-text dump.

- [ ] Write `docs/reports/day1_5_coverage_report.md` with one section per standard:

```text
standard_code
card_id
markdown_source
covered_sections
method_card_fields_filled
manual_summary_notes
needs_pdf_check
review_status
```

Every row must set `needs_pdf_check=true` because this task uses markdown extraction only and does not compare against the original PDF.

### Task 3: Add Evidence Linkage Schema Support and Validate Seed JSON Before Touching Database

**Files:**

- Modify: `enviro-nexus-knowledge/app/schemas/method_card.py`
- Modify: `enviro-nexus-knowledge/app/core/evidence_builder.py`
- Modify: `enviro-nexus-knowledge/app/core/answer_builder.py`
- Modify: `enviro-nexus-knowledge/tests/unit/test_method_card_schema.py`
- Modify: `enviro-nexus-knowledge/tests/unit/test_answer_builder.py`

- [ ] Extend schema tests so invalid `answer_template.evidence_ids` and invalid `measurement.evidence_ids` fail validation when they reference missing evidence ids.

- [ ] Run the focused schema test before implementation:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run pytest tests/unit/test_method_card_schema.py -v
```

Expected before schema support:

```text
fail because AnswerTemplate or Measurement does not yet support required evidence_ids, or because cross-field validation is missing
```

- [ ] Add `evidence_ids` fields and cross-field validation in `app/schemas/method_card.py`.

- [ ] Extend answer evidence collection so `answer_template`, `applicability`, and `measurement` evidence ids are included in `answer.evidence_refs`.

- [ ] Keep answer response stable: do not expose `answer_template.evidence_ids` or `measurement.evidence_ids` as standalone response fields.

- [ ] Run unit schema tests:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run pytest tests/unit/test_method_card_schema.py -v
```

Expected:

```text
passed
```

- [ ] If the schema test only validates pH, update it to validate all MethodCard JSON files and rerun.

### Task 4: Update Tests for Expanded Seed

**Files:**

- Modify: `enviro-nexus-knowledge/tests/unit/test_method_card_schema.py`
- Modify: `enviro-nexus-knowledge/tests/unit/test_factor_matcher.py`
- Modify: `enviro-nexus-knowledge/tests/integration/test_seed_import.py`
- Modify: `enviro-nexus-knowledge/tests/integration/test_factor_query_api.py`

- [ ] Update expected source/card counts to:

```text
source_documents = 5
method_cards = 5
factor_aliases >= 16
```

- [ ] Keep import batch expectation:

```text
After two imports, knowledge_import_batches success count = 2 for this cleaned run.
```

- [ ] Add query assertions:

```text
pH 怎么测？ -> water_ph_hj1147_2020
水样酸碱度用什么标准？ -> water_ph_hj1147_2020
色度怎么测？ -> water_colority_hj1182_2021
CODMn 怎么测？ -> water_permanganate_index_hj1445_2026
烟气黑度怎么测？ -> gas_smoke_blackness_hj1287_2023
非甲烷总烃怎么测？ -> gas_thc_methane_nmhc_hj1332_2023
COD 怎么测？ -> matched=false
```

### Task 5: Clear Business Data

**Files:** no writes.

- [ ] Confirm the user has approved this plan.

- [ ] Start PostgreSQL if needed:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
docker compose up -d postgres
```

- [ ] Ensure migrations are applied:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run alembic upgrade head
```

- [ ] Clear business table rows:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
docker compose exec -T postgres psql -U enviro_nexus -d enviro_nexus_knowledge -c "TRUNCATE factor_aliases, method_cards, source_documents, knowledge_import_batches RESTART IDENTITY CASCADE;"
```

- [ ] Verify business tables are empty:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
docker compose exec -T postgres psql -U enviro_nexus -d enviro_nexus_knowledge -c "SELECT 'source_documents' AS table_name, count(*) FROM source_documents UNION ALL SELECT 'method_cards', count(*) FROM method_cards UNION ALL SELECT 'factor_aliases', count(*) FROM factor_aliases UNION ALL SELECT 'knowledge_import_batches', count(*) FROM knowledge_import_batches ORDER BY table_name;"
```

Expected:

```text
factor_aliases | 0
knowledge_import_batches | 0
method_cards | 0
source_documents | 0
```

### Task 6: Import Twice and Verify Idempotency

**Files:** no writes unless import exposes invalid seed data.

- [ ] First import:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run python -m app.services.import_service --seed data/seed --mode upsert
```

Expected:

```text
status=success cards_count=5 aliases_count=16 batch_id=seed-...
```

If aliases exceed 16 because extra useful aliases were added, record the actual number and keep it consistent in tests.

- [ ] Second import:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run python -m app.services.import_service --seed data/seed --mode upsert
```

Expected:

```text
status=success cards_count=5 aliases_count=16 batch_id=seed-...
```

- [ ] Verify counts:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
docker compose exec -T postgres psql -U enviro_nexus -d enviro_nexus_knowledge -c "SELECT 'source_documents' AS table_name, count(*) FROM source_documents UNION ALL SELECT 'method_cards', count(*) FROM method_cards UNION ALL SELECT 'factor_aliases', count(*) FROM factor_aliases UNION ALL SELECT 'knowledge_import_batches', count(*) FROM knowledge_import_batches ORDER BY table_name;"
```

Expected after two imports:

```text
factor_aliases | 16 or actual alias seed count
knowledge_import_batches | 2
method_cards | 5
source_documents | 5
```

### Task 7: Run Tests

**Files:** no writes unless tests reveal invalid seed or incorrect test expectations.

- [ ] Run unit tests:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run pytest tests/unit -v
```

- [ ] Run full tests:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run pytest -v
```

Expected:

```text
passed
```

Record the exact final test count.

### Task 8: Query Verification

**Files:** no writes.

- [ ] Start API if it is not already running:

```powershell
cd D:\szy\code\my-project\enviro-nexus\enviro-nexus-knowledge
uv run uvicorn app.main:app --host 0.0.0.0 --port 8010
```

- [ ] Query pH:

```powershell
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"pH 怎么测？\"}"
```

Expected:

```text
matched=true
card_id=water_ph_hj1147_2020
answer.evidence_refs is non-empty
```

- [ ] Query COD:

```powershell
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"COD 怎么测？\"}"
```

Expected:

```text
matched=false
card_id=null
```

- [ ] Query CODMn:

```powershell
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"CODMn 怎么测？\"}"
```

Expected:

```text
matched=true
card_id=water_permanganate_index_hj1445_2026
```

### Task 9: Final Safety Check

**Files:** no writes.

- [ ] Check git status:

```powershell
git -c core.quotepath=false status --short
```

- [ ] Confirm no changes under:

```text
enviro-nexus-api
enviro-nexus-web
```

- [ ] Confirm no tracked cache files:

```powershell
git -c core.quotepath=false ls-files | rg "(^|/)(__pycache__/|\\.pytest_cache/|.*\\.py[co]$|.*\\.pyd$)"
```

Expected:

```text
no output
```

## 9. Final Report Format

After implementation, report only these items:

```text
1. 实际创建/修改文件列表
2. 清库前数据库计数
3. 清库后数据库计数
4. import 第一次结果
5. import 第二次幂等结果
6. pytest tests/unit -v 结果
7. uv run pytest -v 结果
8. pH 查询返回摘要
9. COD 查询返回摘要
10. CODMn 查询返回摘要
11. 数据库最终计数
12. 数据覆盖与人工复核报告路径
13. 是否修改 enviro-nexus-api / enviro-nexus-web
14. 报错信息
```

## 10. Approval Gate

Do not execute Task 5 or later until the user explicitly approves this plan.

Plan approval means the user accepts:

- Existing business rows in local PostgreSQL will be cleared.
- The runtime seed dataset will become five MethodCards.
- `COD 怎么测？` remains unmatched.
- `CODMn 怎么测？` becomes matched to HJ 1445-2026.
- This still does not enter Day 2.
