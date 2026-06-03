# Day 1：pH MethodCard 纵向闭环详细执行计划

> 本计划只覆盖 `enviro-nexus-knowledge` 子项目 Day 1。目标是用 `water_ph_hj1147_2020` 一张方法卡打穿最小闭环，不继续扩展 Day 2 数据和功能。

## 1. 本轮目标

只用 `water_ph_hj1147_2020` 一张 MethodCard，打通下面的纵向链路：

```text
seed JSON
-> MethodCard Pydantic v2 Schema 校验
-> import service 幂等导入 PostgreSQL
-> factor_aliases 规则匹配
-> MethodCard 读取
-> answer_builder 结构化回答
-> evidence_builder 依据来源筛选
-> POST /api/v1/factors/query
-> pytest 和 curl 验收
```

完成后应满足：

- pH、PH值、酸碱度能命中 `water_ph_hj1147_2020`。
- COD 不会误命中 pH。
- API 响应包含 `summary`、`standard_code`、`standard_name`、`method_name`、`applicability`、`measurement`、`requirements`、`qa_qc`、`evidence_refs`。
- `evidence_refs` 非空，且只返回本次回答相关依据。
- seed 导入可连续执行两次，不产生重复 source/card/alias 数据。

## 2. 当前基础状态

Day 0 已完成并可复用：

- `pyproject.toml` 已配置 FastAPI、SQLAlchemy、Alembic、psycopg、pydantic-settings、pytest、httpx。
- `docker-compose.yml` 已提供 `postgres:16`，本地端口 `15432`。
- Alembic 已创建四张表：`source_documents`、`method_cards`、`factor_aliases`、`knowledge_import_batches`。
- `app/db/models.py` 已有 ORM 模型。
- `app/db/session.py` 已有 engine 和 `SessionLocal`。
- `app/main.py` 已注册 health route。
- `GET /api/v1/health` 已真实检查数据库。

本轮不新增 migration。Day 1 只使用 Day 0 已有表结构。

## 3. 范围边界

本轮只允许修改：

```text
enviro-nexus-knowledge/
```

禁止修改：

```text
enviro-nexus-api/
enviro-nexus-web/
```

本轮不做：

- 不补色度、高锰酸盐指数、烟气黑度、总烃、甲烷、非甲烷总烃。
- 不做 PDF 自动抽取。
- 不读取、不解析 PDF，`source_documents.file_path` 只作为来源路径元数据记录。
- 不引入大模型。
- 不引入向量检索。
- 不引入 pgvector。
- 不做后台管理 UI。
- 不做任务单解析。
- 不继续做 Day 2。

## 4. 文件清单与职责

### 4.1 新增应用代码

```text
app/schemas/__init__.py
app/schemas/method_card.py
app/schemas/query.py
app/schemas/response.py
app/core/__init__.py
app/core/normalizer.py
app/core/factor_matcher.py
app/core/answer_builder.py
app/core/evidence_builder.py
app/db/repositories.py
app/services/__init__.py
app/services/import_service.py
app/services/query_service.py
app/api/routes/factor_query.py
```

职责说明：

- `method_card.py`：定义 MethodCard v0.1 Pydantic 模型和跨字段校验。
- `query.py`：定义 `POST /api/v1/factors/query` 请求模型。
- `response.py`：定义查询响应模型，统一命中和未命中响应结构。
- `normalizer.py`：实现查询文本和别名归一化。
- `factor_matcher.py`：实现确定性别名匹配和候选排序。
- `answer_builder.py`：从 MethodCard 组装前端可展示结构化回答。
- `evidence_builder.py`：筛选回答字段关联的 evidence_refs。
- `repositories.py`：封装数据库 upsert、查询、计数等持久化操作。
- `import_service.py`：实现 seed 导入和 CLI。
- `query_service.py`：编排 normalize、match、read card、build answer。
- `factor_query.py`：提供 FastAPI 查询路由。

### 4.2 修改应用代码

```text
app/main.py
README.md
```

修改内容：

- `app/main.py` 注册 `factor_query` route。
- `README.md` 增加 Day 1 说明、导入命令、测试命令、curl 示例。

### 4.3 新增 seed 数据

```text
data/seed/source_documents.json
data/seed/factor_aliases.json
data/seed/sample_queries.json
data/seed/method_cards/water_ph_hj1147_2020.json
```

职责说明：

- `source_documents.json`：登记 HJ 1147-2020 来源文件。
- `water_ph_hj1147_2020.json`：pH 单张 MethodCard 完整结构。
- `factor_aliases.json`：pH 查询别名到卡片的运行态映射。
- `sample_queries.json`：本轮验收问题集。

### 4.4 新增测试

```text
tests/unit/test_method_card_schema.py
tests/unit/test_normalizer.py
tests/unit/test_factor_matcher.py
tests/unit/test_answer_builder.py
tests/integration/test_seed_import.py
tests/integration/test_factor_query_api.py
```

测试职责：

- schema 测试覆盖 MethodCard seed 正常校验和关键非法结构。
- normalizer 测试覆盖 pH、PH值、COD、酸碱度。
- matcher 测试覆盖 ph 命中、酸碱度命中、cod 不命中，并提前覆盖 `cod` 不得因为 `codmn` 包含 `cod` 而命中。
- answer_builder 测试覆盖结构化回答字段和 evidence_refs。
- import 集成测试覆盖导入、计数和幂等。
- API 集成测试覆盖 pH 命中、酸碱度命中、COD 未命中。
- integration 测试必须使用真实 PostgreSQL，不允许改用 SQLite，不允许 mock 数据库。运行前默认已执行 `docker compose up -d postgres` 和 `uv run alembic upgrade head`。

## 5. 数据设计

### 5.1 source_documents.json

本轮只包含 1 条来源文档：

```json
{
  "doc_id": "doc_hj1147_2020",
  "source_type": "standard",
  "title": "水质 pH 值的测定 电极法",
  "standard_code": "HJ 1147-2020",
  "file_path": "files/poc-files/水质 pH的测定 电极法 HJ 1147-2020.pdf",
  "status": "active",
  "metadata": {
    "category": "水质",
    "manual_extract_status": "completed"
  }
}
```

`file_path` 只用于记录来源路径元数据。Day 1 import service 可以校验 `doc_id`、`standard_code`、`status` 等结构字段，但不能因为本地 PDF 文件不存在而阻塞导入；PDF 文件存在性校验留到后续数据治理阶段。

### 5.2 water_ph_hj1147_2020.json

关键约束：

- `schema_version` 固定为 `method_card.v0.1`。
- `card_id` 固定为 `water_ph_hj1147_2020`。
- `card_version` 为 `1`。
- `identity.category` 为 `水质`。
- `identity.factor` 为 `pH 值`。
- `identity.factors` 至少包含 `pH 值`，别名为 `pH`、`PH`、`pH值`、`酸碱度`。
- `requirements` 至少 3 条，类型分别为 `sample_collection`、`instrument`、`result_expression`。
- `qa_qc` 至少 1 条。
- `evidence_refs` 至少 5 条。
- `governance.review_status=approved`。
- `governance.answer_visibility=enabled`。

`requirements.type` 禁止使用 `sample`，只能使用固定枚举：

```text
sample_collection
sample_preservation
instrument
interference
analysis_step
result_expression
field_condition
safety_note
other
```

### 5.3 factor_aliases.json

数据库唯一约束为：

```sql
UNIQUE(normalized_alias, card_id)
```

所以本轮不把 `pH`、`PH`、`pH值` 三条都写成 `normalized_alias=ph`。运行态 alias seed 采用去重后的最小集合：

```json
[
  {
    "alias": "pH 值",
    "normalized_alias": "ph",
    "factor": "pH 值",
    "card_id": "water_ph_hj1147_2020",
    "priority": 10,
    "enabled": true
  },
  {
    "alias": "酸碱度",
    "normalized_alias": "酸碱度",
    "factor": "pH 值",
    "card_id": "water_ph_hj1147_2020",
    "priority": 30,
    "enabled": true
  }
]
```

展示别名仍完整保存在 MethodCard 的 `identity.aliases` 中。

### 5.4 sample_queries.json

本轮只放 pH 和一个未命中：

```json
[
  {
    "query": "pH 怎么测？",
    "expected_card_id": "water_ph_hj1147_2020",
    "expected_matched": true
  },
  {
    "query": "水样酸碱度用什么标准？",
    "expected_card_id": "water_ph_hj1147_2020",
    "expected_matched": true
  },
  {
    "query": "PH值检测方法",
    "expected_card_id": "water_ph_hj1147_2020",
    "expected_matched": true
  },
  {
    "query": "COD 怎么测？",
    "expected_card_id": null,
    "expected_matched": false
  }
]
```

## 6. 实现任务拆分

### Task 1：写 MethodCard Schema 和 seed 校验测试

目标：先用测试定义 MethodCard v0.1 的合法和非法结构。

涉及文件：

```text
tests/unit/test_method_card_schema.py
app/schemas/__init__.py
app/schemas/method_card.py
data/seed/source_documents.json
data/seed/method_cards/water_ph_hj1147_2020.json
```

步骤：

1. 写 `test_ph_method_card_seed_passes_schema_validation`。
2. 写 `test_requirements_type_rejects_sample`。
3. 写 `test_requirement_evidence_ids_must_exist`。
4. 写 `test_qa_qc_evidence_ids_must_exist`。
5. 运行：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest tests/unit/test_method_card_schema.py -v
```

预期红灯：

```text
ModuleNotFoundError: No module named 'app.schemas'
```

6. 创建 seed JSON 和 `MethodCard` Pydantic 模型。
7. 重跑该测试，预期通过。

MethodCard 模型实现要点：

- 顶层字段至少包含 `schema_version`、`card_id`、`card_version`、`identity`、`applicability`、`measurement`、`requirements`、`qa_qc`、`answer_template`、`source_document`、`evidence_refs`、`governance`、`change_log`、`extensions`。
- `schema_version` 用 `Literal["method_card.v0.1"]`。
- `card_id` 使用正则校验 `^[a-z0-9_]+$`。
- `card_version >= 1`。
- `identity.factor`、`identity.factors`、`identity.aliases` 都不能为空。
- `identity.aliases` 必须覆盖所有 `identity.factors[].aliases`。
- `requirements` 和 `qa_qc` 都不能为空。
- `evidence_refs.evidence_id` 不允许重复。
- `requirements[].evidence_ids` 和 `qa_qc[].evidence_ids` 必须都能指向已有 `evidence_refs`。

### Task 2：实现 normalizer

目标：把用户输入和别名变成可匹配的稳定字符串。

涉及文件：

```text
tests/unit/test_normalizer.py
app/core/__init__.py
app/core/normalizer.py
```

步骤：

1. 写测试覆盖：

```text
"pH 怎么测？" -> "ph"
"PH值检测方法" -> "ph"
"COD 怎么测？" -> "cod"
"水样酸碱度用什么标准？" 至少保留 "酸碱度"
"pH值" alias -> "ph"
```

2. 运行：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest tests/unit/test_normalizer.py -v
```

预期红灯：

```text
ModuleNotFoundError: No module named 'app.core'
```

3. 实现 `normalize_query(text: str) -> str` 和 `normalize_alias(text: str) -> str`。

实现规则：

- 去除首尾空白。
- 全角转半角。
- 英文统一小写。
- `pH`、`PH`、`ph`、`pH值`、`PH值` 统一为 `ph`。
- 移除问句词：`怎么测`、`用什么方法`、`用哪个标准`、`用什么标准`、`标准`、`检测`、`测定`、`方法`。
- 移除无意义标点。
- 合并空白。
- 中文关键词保留，例如 `酸碱度`。

normalizer 的处理顺序必须固定为：

```text
trim
-> 全角转半角
-> 英文小写
-> 特殊归一 pH、PH、pH值、PH值 为 ph
-> 移除问句词和业务噪声词
-> 移除无意义标点
-> 合并空白
```

4. 重跑 normalizer 测试，预期通过。

### Task 3：实现 answer_builder 和 evidence_builder

目标：从 MethodCard 模型生成 API 可返回的结构化回答。

涉及文件：

```text
tests/unit/test_answer_builder.py
app/core/answer_builder.py
app/core/evidence_builder.py
```

步骤：

1. 写测试：读取 pH seed，构造 `MethodCard`，调用 `build_answer(card)`。
2. 断言返回包含：

```text
summary
standard_code
standard_name
method_name
applicability
measurement
requirements
qa_qc
evidence_refs
```

3. 运行：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest tests/unit/test_answer_builder.py -v
```

预期红灯：

```text
ModuleNotFoundError: No module named 'app.core.answer_builder'
```

4. 实现 `collect_answer_evidence_refs(card: MethodCard) -> list[dict]`：

- 收集 `requirements[].evidence_ids`。
- 收集 `qa_qc[].evidence_ids`。
- 可加入 `applicability.scope_summary` 对应的 evidence。
- 去重后按 MethodCard 中 `evidence_refs` 原顺序返回。

5. 实现 `build_answer(card: MethodCard) -> dict`：

- `summary` 取 `answer_template.short_answer`。
- `standard_code`、`standard_name`、`method_name` 取 `identity`。
- `applicability` 取 `applicability.scope_summary`。
- `measurement` 返回 detection/lower/upper/unit 等字段。
- `requirements` 返回 `type`、`title`、`content`。
- `qa_qc` 返回 `title`、`content`。
- `evidence_refs` 返回 evidence builder 的结果。
- 不返回 `governance`、`change_log`、内部文件路径或标准全文。

6. 重跑 answer_builder 测试，预期通过。

### Task 4：实现 factor matcher 纯函数

目标：先用内存候选验证匹配策略，避免一开始耦合数据库。

涉及文件：

```text
tests/unit/test_factor_matcher.py
app/core/factor_matcher.py
```

步骤：

1. 写测试候选：

```text
normalized_alias=ph, priority=10, card_id=water_ph_hj1147_2020
normalized_alias=酸碱度, priority=30, card_id=water_ph_hj1147_2020
```

2. 断言：

```text
ph 命中 water_ph_hj1147_2020, confidence=1.0
水样酸碱度 命中 water_ph_hj1147_2020
cod 不命中
cod 不得因为 codmn 包含 cod 而命中
```

3. 运行：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest tests/unit/test_factor_matcher.py -v
```

预期红灯：

```text
ModuleNotFoundError: No module named 'app.core.factor_matcher'
```

4. 实现：

```text
AliasCandidate
MatchResult
choose_best_match(normalized_query, candidates)
```

匹配规则：

- 跳过 `enabled=false`。
- 精确匹配：`normalized_query == normalized_alias`，`confidence=1.0`。
- 查询包含别名：`normalized_alias in normalized_query`，`confidence=0.9`。
- 别名包含查询：`normalized_query in normalized_alias`，`confidence=0.8`。
- 英文/数字缩写保护：如果 `normalized_query` 和 `normalized_alias` 都只包含 ASCII 字母数字，且二者不完全相等，则不命中；不能使用包含关系产生命中。尤其要保证后续 `cod` 不会因为 `codmn` 包含 `cod` 而误命中 CODMn。
- 排序：`confidence` 降序，`priority` 升序。
- 无候选返回 `None`。
- 不做拼音、编辑距离或大模型判断。

5. 重跑 matcher 测试，预期通过。

### Task 5：实现数据库 repository

目标：集中处理 Day 1 的数据写入和读取，避免业务服务直接拼 SQL。

涉及文件：

```text
app/db/repositories.py
```

需要实现的能力：

- `upsert_source_document(session, source: dict) -> None`
- `upsert_method_card(session, card: MethodCard) -> None`
- `upsert_factor_alias(session, alias: dict) -> None`
- `insert_import_batch(session, ...) -> None`
- `list_alias_candidates(session) -> list[AliasCandidate]`
- `get_enabled_method_card_json(session, card_id: str) -> dict | None`
- `count_table(session, table_name: str) -> int` 可只用于测试辅助时保留在测试里，不强制放 repository。

实现要点：

- PostgreSQL upsert 使用 SQLAlchemy PostgreSQL `insert(...).on_conflict_do_update(...)`。
- `source_documents` 冲突键：`doc_id`。
- `method_cards` 冲突键：`card_id`。
- `factor_aliases` 冲突键：`normalized_alias, card_id`。
- `method_cards.card_json` 保存完整 MethodCard `model_dump(mode="json")`。
- `method_cards.source_doc_id` 取 `card.source_document.doc_id`。
- `review_status` 取 `card.governance.review_status`。
- `answer_visibility` 取 `card.governance.answer_visibility`。
- alias 查询必须 join `method_cards`，过滤 `factor_aliases.enabled=true`、`method_cards.review_status='approved'`、`method_cards.answer_visibility='enabled'`。

### Task 6：实现 import service 和 seed import 集成测试

目标：用 CLI 把 pH seed 幂等导入 PostgreSQL。

涉及文件：

```text
tests/integration/test_seed_import.py
app/services/__init__.py
app/services/import_service.py
data/seed/source_documents.json
data/seed/factor_aliases.json
data/seed/sample_queries.json
data/seed/method_cards/water_ph_hj1147_2020.json
```

步骤：

1. 写集成测试：

```text
导入前清空 factor_aliases、method_cards、source_documents、knowledge_import_batches
执行 import_seed(Path("data/seed"), mode="upsert")
再次执行 import_seed(Path("data/seed"), mode="upsert")
source_documents count = 1
method_cards count = 1
factor_aliases count >= 2
knowledge_import_batches status=success count = 2
```

2. 确保 PostgreSQL 已启动并迁移：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
```

本集成测试依赖 Docker PostgreSQL 和 Alembic migration，必须连接真实 PostgreSQL，不允许为了测试独立运行改成 SQLite 或 mock database。

3. 运行：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest tests/integration/test_seed_import.py -v
```

预期红灯：

```text
ModuleNotFoundError: No module named 'app.services'
```

4. 实现 `ImportResult` 和 `import_seed(seed_path: Path, mode: str) -> ImportResult`。

导入流程：

```text
读取 source_documents.json
读取 method_cards/*.json
读取 factor_aliases.json
校验 MethodCard
校验 card.source_document.doc_id 存在于 source_documents
校验 standard_code 一致
开启事务
upsert source_documents
upsert method_cards
upsert factor_aliases
insert knowledge_import_batches(status=success)
提交事务
失败则 rollback，并尝试记录失败 batch 或返回失败结果
```

CLI：

```bash
uv run python -m app.services.import_service --seed data/seed --mode upsert
```

CLI 成功输出建议：

```text
status=success cards_count=1 aliases_count=2
```

5. 重跑 seed import 集成测试，预期通过。

### Task 7：实现 query service 和 factor query API

目标：打通 HTTP 查询闭环。

涉及文件：

```text
tests/integration/test_factor_query_api.py
app/schemas/query.py
app/schemas/response.py
app/services/query_service.py
app/api/routes/factor_query.py
app/main.py
```

步骤：

1. 写 API 集成测试：

```text
POST /api/v1/factors/query {"query": "pH 怎么测？"} 命中 water_ph_hj1147_2020
返回 answer.evidence_refs 非空
POST /api/v1/factors/query {"query": "水样酸碱度用什么标准？"} 命中 water_ph_hj1147_2020
POST /api/v1/factors/query {"query": "COD 怎么测？"} 返回 matched=false
```

2. 运行：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest tests/integration/test_factor_query_api.py -v
```

预期红灯：

```text
ModuleNotFoundError: No module named 'app.api.routes.factor_query'
```

3. 实现 `FactorQueryRequest`：

```text
query: str
```

4. 实现响应模型：

```text
api_version
matched
factor
matched_alias
match_confidence
card_id
answer
warnings
```

5. 实现 `query_factor(query: str, session) -> dict`：

```text
query strip 后为空 -> 抛出 empty_query 业务异常
normalized_query = normalize_query(query)
candidates = repository.list_alias_candidates(session)
match = choose_best_match(normalized_query, candidates)
无 match -> unmatched response
有 match -> 读取 enabled MethodCard JSON
MethodCard.model_validate(card_json)
build_answer(card)
返回 matched response
```

6. 实现 `POST /api/v1/factors/query`：

- 正常命中返回 200。
- 未命中返回 200。
- 空字符串返回 400，响应包含 `error_code=empty_query`。
- 数据库错误返回 503。
- 缺少 `query` 使用 FastAPI 默认 422。

7. 修改 `app/main.py` 注册 route：

```text
app.include_router(factor_query_router, prefix=f"/api/{settings.api_version}")
```

8. 重跑 API 集成测试，预期通过。

### Task 8：更新 README

目标：让 Day 1 可按 README 复现。

涉及文件：

```text
README.md
```

新增内容：

- Day 1 目标说明。
- seed 导入命令。
- 连续导入幂等说明。
- API 查询 curl 示例。
- 测试前需要 PostgreSQL 运行并执行 migration。

README 命令写成 Windows Git Bash 可复制的一行：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run python -m app.services.import_service --seed data/seed --mode upsert
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest -v
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"pH 怎么测？\"}"
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"COD 怎么测？\"}"
```

### Task 9：全量验证和回归

目标：用真实数据库、真实导入和真实 HTTP 请求验收。

执行命令：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run python -m app.services.import_service --seed data/seed --mode upsert
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run python -m app.services.import_service --seed data/seed --mode upsert
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest -v
```

HTTP 验收：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"pH 怎么测？\"}"
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"COD 怎么测？\"}"
```

pH curl 预期关键字段：

```json
{
  "api_version": "v1",
  "matched": true,
  "factor": "pH 值",
  "card_id": "water_ph_hj1147_2020",
  "answer": {
    "standard_code": "HJ 1147-2020",
    "standard_name": "水质 pH 值的测定 电极法",
    "method_name": "电极法",
    "evidence_refs": [
      {
        "source_title": "HJ 1147-2020",
        "section": "7 样品",
        "page": 3,
        "summary": "标准规定样品可现场测定；实验室测定时采样瓶应充满并立即密封，2 h 内完成测定。"
      }
    ]
  }
}
```

示例、测试和实际验收中的 `answer.evidence_refs` 都必须非空。

COD curl 预期：

```json
{
  "api_version": "v1",
  "matched": false,
  "factor": null,
  "matched_alias": null,
  "match_confidence": 0.0,
  "card_id": null,
  "answer": null,
  "warnings": [
    "当前知识库暂未收录该检测因子，请人工确认后再使用。"
  ]
}
```

## 7. 错误处理要求

### 7.1 import service

必须处理：

- seed 路径不存在。
- `source_documents.json` 不存在或 JSON 格式错误。
- `method_cards/*.json` 不存在。
- MethodCard schema 校验失败。
- MethodCard `source_document.doc_id` 未登记。
- MethodCard `standard_code` 与 source document 不一致。
- factor alias 指向不存在的 MethodCard。
- `source_documents.file_path` 只校验为非空字符串，不做本地文件存在性校验。
- 数据库写入失败。

失败时要求：

- 事务回滚。
- CLI 返回非 0 退出码或抛出清晰异常。
- 错误信息能定位失败文件或失败校验项。

### 7.2 query API

必须处理：

- `query=""` 或全空白：HTTP 400，业务错误 `empty_query`。
- 请求体缺少 `query`：FastAPI 422。
- 数据库不可用：HTTP 503。
- 未命中：HTTP 200，`matched=false`。

## 8. 数据库幂等策略

导入两次后应满足：

```sql
SELECT count(*) FROM source_documents; -- 1
SELECT count(*) FROM method_cards; -- 1
SELECT count(*) FROM factor_aliases; -- >= 2
SELECT count(*) FROM knowledge_import_batches WHERE status = 'success'; -- 每次导入新增 1 条
```

说明：

- source/card/alias 是运行态数据，必须幂等。
- import batch 是导入审计记录，每次导入都可以新增。
- 不修改 Day 0 的唯一约束。
- 不通过删除唯一约束解决 alias 冲突。

## 9. 最终验收标准

本轮完成必须全部满足：

1. `uv run python -m app.services.import_service --seed data/seed --mode upsert` 成功。
2. 连续执行两次 import 不产生重复 source/card/alias 数据。
3. `uv run pytest -v` 全部通过。
4. `POST /api/v1/factors/query` 输入 `pH 怎么测？` 命中 `water_ph_hj1147_2020`。
5. pH 响应包含 `summary`、`standard_code`、`standard_name`、`method_name`、`applicability`、`measurement`、`requirements`、`qa_qc`、`evidence_refs`。
6. pH 响应的 `answer.evidence_refs` 非空。
7. `POST /api/v1/factors/query` 输入 `COD 怎么测？` 返回 `matched=false`。
8. `GET /api/v1/health` 仍然返回 `database=ok`。
9. 没有修改 `enviro-nexus-api` 和 `enviro-nexus-web`。
10. 没有继续做 Day 2。

## 10. 完成后汇报格式

完成实现后汇报：

1. 实际创建或修改的文件列表。
2. 每个文件的作用。
3. 执行过的命令及结果。
4. import service 执行结果。
5. pytest 结果。
6. curl 查询 pH 的返回结果。
7. curl 查询 COD 的返回结果。
8. 如有失败，贴出完整报错和修复过程。
9. 明确说明没有继续做 Day 2。

## 11. 补充修正要求

1. pH curl 预期响应示例中，`answer.evidence_refs` 不允许写成空数组。示例和测试都必须体现 `evidence_refs` 非空。
2. factor matcher 中，对于英文/数字缩写类 `normalized_query` 和 `normalized_alias`，如果二者不完全相等，不允许使用包含关系命中。尤其要保证后续 `cod` 不会因为 `codmn` 包含 `cod` 而误命中 CODMn。本轮虽然没有 CODMn alias，也要提前写好保护逻辑和测试。
3. normalizer 的处理顺序应为：trim、全角转半角、英文小写、特殊归一 pH/PH/pH值/PH值 为 ph、移除问句词、移除无意义标点、合并空白。
4. integration 测试必须使用真实 PostgreSQL，不要改用 SQLite，不要 mock 数据库。运行前默认已执行：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
```

5. Day 1 不读取、不解析 PDF，`source_documents.file_path` 只作为来源路径元数据记录。import service 不得因为本地 PDF 文件不存在而阻塞导入。
