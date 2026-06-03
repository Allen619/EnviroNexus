# Day 1 pH MethodCard 纵向闭环验收报告

## Day 1 目标

Day 1 的目标是只使用 `water_ph_hj1147_2020` 一张 pH MethodCard，打通知识库底座的最小纵向闭环，验证 seed 数据、Schema 校验、数据库导入、规则匹配、结构化回答和 API 查询可以端到端工作。

本轮不扩展其他标准卡，不进入 Day 2。

## 实际完成的主链路

```text
seed JSON
-> MethodCard Schema
-> import service
-> PostgreSQL
-> factor matcher
-> answer_builder
-> evidence_builder
-> POST /api/v1/factors/query
```

链路说明：

- `seed JSON`：使用 `data/seed/method_cards/water_ph_hj1147_2020.json`、`source_documents.json`、`factor_aliases.json`。
- `MethodCard Schema`：使用 Pydantic v2 校验 MethodCard 结构、枚举、evidence 引用和 alias 覆盖关系。
- `import service`：通过 `uv run python -m app.services.import_service --seed data/seed --mode upsert` 幂等导入。
- `PostgreSQL`：数据写入 `source_documents`、`method_cards`、`factor_aliases`、`knowledge_import_batches`。
- `factor matcher`：确定性规则匹配 `ph`、`酸碱度`，并保护 `cod` 不因 `codmn` 包含关系误命中。
- `answer_builder`：从 MethodCard 生成结构化回答字段。
- `evidence_builder`：只返回与回答相关的 evidence refs。
- `POST /api/v1/factors/query`：pH 查询命中，COD 查询返回未命中。

## 实际创建/修改的核心文件

核心实现文件：

```text
enviro-nexus-knowledge/app/schemas/method_card.py
enviro-nexus-knowledge/app/schemas/query.py
enviro-nexus-knowledge/app/schemas/response.py
enviro-nexus-knowledge/app/core/normalizer.py
enviro-nexus-knowledge/app/core/factor_matcher.py
enviro-nexus-knowledge/app/core/answer_builder.py
enviro-nexus-knowledge/app/core/evidence_builder.py
enviro-nexus-knowledge/app/db/repositories.py
enviro-nexus-knowledge/app/services/import_service.py
enviro-nexus-knowledge/app/services/query_service.py
enviro-nexus-knowledge/app/api/routes/factor_query.py
enviro-nexus-knowledge/app/main.py
```

seed 数据文件：

```text
enviro-nexus-knowledge/data/seed/source_documents.json
enviro-nexus-knowledge/data/seed/factor_aliases.json
enviro-nexus-knowledge/data/seed/sample_queries.json
enviro-nexus-knowledge/data/seed/method_cards/water_ph_hj1147_2020.json
```

测试文件：

```text
enviro-nexus-knowledge/tests/unit/test_method_card_schema.py
enviro-nexus-knowledge/tests/unit/test_normalizer.py
enviro-nexus-knowledge/tests/unit/test_answer_builder.py
enviro-nexus-knowledge/tests/unit/test_factor_matcher.py
enviro-nexus-knowledge/tests/integration/test_seed_import.py
enviro-nexus-knowledge/tests/integration/test_factor_query_api.py
```

文档文件：

```text
enviro-nexus-knowledge/README.md
enviro-nexus-knowledge/docs/plans/day1-ph-method-card-vertical-slice-plan.md
enviro-nexus-knowledge/docs/reports/day1-ph-vertical-slice-acceptance.md
```

## import 第一次结果

执行命令：

```bash
uv run python -m app.services.import_service --seed data/seed --mode upsert
```

结果：

```text
status=success cards_count=1 aliases_count=2 batch_id=seed-70b9e099-4aeb-42b6-8e58-0e8cce2c5ea9
```

## import 第二次幂等结果

执行命令：

```bash
uv run python -m app.services.import_service --seed data/seed --mode upsert
```

结果：

```text
status=success cards_count=1 aliases_count=2 batch_id=seed-e09d0065-084d-488f-b9ff-8be415e4fd15
```

说明：

- `source_documents` 幂等保持 1 条。
- `method_cards` 幂等保持 1 条。
- `factor_aliases` 幂等保持 2 条。
- `knowledge_import_batches` 是导入审计记录，每次导入可新增 1 条。

## pytest 结果

最终全量测试结果：

```text
22 passed
```

覆盖范围包括：

- MethodCard Schema 单元测试。
- normalizer 单元测试。
- factor matcher 单元测试。
- answer builder / evidence builder 单元测试。
- seed import 真实 PostgreSQL 集成测试。
- factor query API 集成测试。
- health API 集成测试。

## pH 查询结果摘要

请求：

```http
POST /api/v1/factors/query
```

请求体：

```json
{"query":"pH 怎么测？"}
```

结果摘要：

```json
{
  "api_version": "v1",
  "matched": true,
  "factor": "pH 值",
  "matched_alias": "pH 值",
  "match_confidence": 1.0,
  "card_id": "water_ph_hj1147_2020",
  "answer": {
    "standard_code": "HJ 1147-2020",
    "standard_name": "水质 pH 值的测定 电极法",
    "method_name": "电极法",
    "evidence_refs": "非空"
  },
  "warnings": []
}
```

## COD 查询结果摘要

请求：

```http
POST /api/v1/factors/query
```

请求体：

```json
{"query":"COD 怎么测？"}
```

结果摘要：

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

## 未修改范围

本轮明确未修改：

```text
enviro-nexus-api/
enviro-nexus-web/
```

## 当前边界

Day 1 当前只覆盖：

```text
water_ph_hj1147_2020
```

当前没有覆盖：

- 5 本 PDF 的全量内容。
- 色度。
- 高锰酸盐指数。
- 烟气黑度。
- 总烃。
- 甲烷。
- 非甲烷总烃。

当前不做：

- PDF 自动解析。
- RAG。
- 大模型问答。
- 向量检索。
- 后台管理 UI。
- 任务单解析。
- Day 2 功能。

`source_documents.file_path` 只作为来源路径元数据记录，Day 1 import service 不会因为本地 PDF 文件不存在而阻塞导入。

## 下一步建议

建议进入 Day 1.5 / Day 2 前，先做前置数据准备：

1. 人工解析 5 本 PDF。
2. 每本 PDF 形成一份 extraction markdown。
3. extraction markdown 中明确标准编号、适用范围、检测方法、样品要求、仪器要求、干扰因素、结果表示、质量保证和质量控制、证据页码与章节。
4. 再基于 extraction markdown 生成更多 MethodCard seed。
5. 在新增标准卡前继续沿用规则：先写详细计划文件，确认后再实现代码。
