# EnviroNexus POC 阶段知识库底座系统分析设计文档

## 0. 文档信息

| 项目 | 内容 |
| --- | --- |
| 项目名称 | 环检智枢 EnviroNexus |
| 子项目 | `enviro-nexus-knowledge` |
| 负责人 | 苏振宇 |
| 文档定位 | POC 阶段知识库底座系统分析与详细设计 |
| 文档版本 | v0.1 |
| 编写日期 | 2026-06-02 |
| 输入资料 | `docs/prd/最小POC功能实现方案.md`、`files/poc-files/` 下 5 份标准 PDF |
| 默认边界 | 只设计和实施 `enviro-nexus-knowledge`；`enviro-nexus-api`、`enviro-nexus-web` 默认只读，不在本 POC 中修改 |

## 1. POC 目标

本 POC 的目标是跑通环保检测标准方法知识服务的最小闭环：

```text
检测因子或简单问题
-> 因子识别与别名匹配
-> 查询 MethodCard 方法卡
-> 组装结构化回答
-> 附加依据来源
-> 通过 API 返回
-> 支撑后端和前端展示
```

POC 不追求一次性完成全部环保业务系统，而是先证明标准方法知识可以被结构化、被查询、被解释、被追溯，并为后续任务单解析、排单辅助、设备耗材匹配、采样要求提示打底。

## 2. 本次资料范围

本轮资料来自 `files/poc-files/`。POC 首批 MethodCard 只覆盖这 5 份标准，不额外扩展到其他资料。

| 序号 | 标准文件 | 建议 `card_id` | 检测因子 | 类别 | 方法名称 | POC 重点字段 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `HJ 1287-2023 固定污染源废气 烟气黑度的测定 林格曼望远镜法.pdf` | `gas_smoke_blackness_hj1287_2023` | 烟气黑度 | 固定污染源废气 | 林格曼望远镜法 | 现场观测条件、观测频次、结果表示、质控要求 |
| 2 | `HJ 1332-2023 固定污染源废气 总烃、甲烷和非甲烷总烃的测定 便携式气相色谱-氢火焰离子化检测器法.pdf` | `gas_thc_methane_nmhc_hj1332_2023` | 总烃、甲烷、非甲烷总烃 | 固定污染源废气 | 便携式气相色谱-氢火焰离子化检测器法 | 适用范围、检出限、干扰消除、采样与测定、结果计算、仪器核查 |
| 3 | `HJ 1445-2026 水质 高锰酸盐指数的测定 草酸钠还原酸性滴定法.pdf` | `water_permanganate_index_hj1445_2026` | 高锰酸盐指数 | 水质 | 草酸钠还原酸性滴定法 | 适用范围、氯离子限制、样品保存、分析步骤、质控要求 |
| 4 | `水质 pH的测定 电极法 HJ 1147-2020.pdf` | `water_ph_hj1147_2020` | pH 值 | 水质 | 电极法 | 适用范围、现场/实验室测定、样品时效、仪器校准、结果表示、质控 |
| 5 | `水质 色度的测定 稀释倍数法 HJ 1182-2021.pdf` | `water_colority_hj1182_2021` | 色度 | 水质 | 稀释倍数法 | 样品保存、颜色描述、pH 联动、结果表示、人员要求 |

`card_id` 命名在开工前冻结：

1. 固定污染源废气统一使用 `gas_` 前缀，不使用 `air_`，避免与环境空气 `ambient air` 混淆。
2. 水质统一使用 `water_` 前缀。
3. 命名格式为 `{category}_{factor_or_group}_{standard_code}_{year}`，只使用小写字母、数字和下划线。
4. `card_id` 一旦被接口、数据库或前端依赖，后续不得直接改名；确需调整时新增迁移映射。

## 3. POC 范围与非范围

### 3.1 本阶段做什么

1. 建立 MethodCard v0.1 数据结构。
2. 为 5 份标准手工整理首批方法卡。
3. 建立因子别名表，支持常见中文、英文缩写、业务俗称匹配。
4. 使用 PostgreSQL 作为主库，MethodCard 正文使用 JSONB 保存，稳定检索字段拆成关系列。
5. 使用 Docker 启动 PostgreSQL，并用 named volume 持久化数据。
6. 使用 seed JSON 文件作为可审查、可迁移、可重复导入的数据源。
7. 提供知识服务 API：健康检查、因子查询、方法卡详情。
8. 输出接口契约，作为后端和前端联调依据。
9. 建立 POC 测试集，覆盖 5 个 MethodCard 和核心查询路径。

### 3.2 本阶段不做什么

1. 不做标准 PDF 全自动抽取和自动入库。
2. 不做向量检索和大模型问答生成。
3. 不做复杂权限、审核流、后台管理 UI。
4. 不做批量任务单解析。
5. 不修改 `enviro-nexus-api` 和 `enviro-nexus-web`，除非后续明确要求。
6. 不把标准全文作为回答内容返回，只返回结构化摘要和依据定位。

## 4. 总体架构设计

POC 阶段的知识服务采用“人工结构化 + 数据库持久化 + 规则查询”的架构。

```mermaid
flowchart LR
  A["标准 PDF 文件<br/>files/poc-files"] --> B["人工结构化整理<br/>MethodCard Seed JSON"]
  B --> C["Schema 校验<br/>Pydantic Model"]
  C --> D["Seed Importer<br/>幂等导入"]
  D --> E[("PostgreSQL<br/>关系字段 + JSONB")]
  E --> F["Factor Matcher<br/>别名匹配"]
  E --> G["MethodCard Store<br/>方法卡查询"]
  F --> H["Query Service<br/>查询编排"]
  G --> H
  H --> I["Answer Builder<br/>结构化回答"]
  I --> J["Evidence Builder<br/>依据来源"]
  J --> K["FastAPI<br/>/api/v1/factors/query"]
```

架构原则：

1. 标准资料先进入 seed JSON，保证数据可评审、可追踪、可重放。
2. PostgreSQL 存运行态数据，避免后期从纯 JSON 文件迁移时痛苦。
3. JSONB 保存 MethodCard 完整结构，关系列保存高频查询和治理字段。
4. POC 查询先用确定性规则，不引入大模型的不确定性。
5. 每个回答必须附带依据来源，避免知识服务变成不可解释的文本拼接。

## 5. 技术选型

| 方向 | 推荐选型 | 原因 |
| --- | --- | --- |
| Web 框架 | FastAPI | Python 生态成熟，接口开发快，自动 OpenAPI，适合 POC |
| 包管理 | uv | 与 PRD 一致，依赖锁定清晰，启动速度快 |
| 数据库 | PostgreSQL 16+ | 同时支持关系模型、JSONB、GIN 索引，后续可接 pgvector |
| JSON 字段 | PostgreSQL JSONB | 适合保存可演进的 MethodCard 正文，能查询和索引，不只是字符串 |
| ORM/SQL | SQLAlchemy 2.x | 迁移和测试生态稳定 |
| 迁移工具 | Alembic | 表结构版本可控，方便后续迭代 |
| 数据校验 | Pydantic v2 | 与 FastAPI 兼容，适合 MethodCard Schema 校验 |
| 测试 | pytest + httpx | 覆盖纯函数、仓储层和 API 层 |
| 本地环境 | Docker Compose | PostgreSQL 独立运行，数据卷可迁移 |

不推荐 MongoDB 作为本 POC 主库。原因是当前知识库不仅有 JSON 文档，还有 `alias -> card_id`、`card -> source_document`、审核状态、版本、导入批次、接口查询等关系。PostgreSQL 能同时处理关系数据和 JSONB，迁移路径更稳。

## 6. 目录结构设计

建议在 `enviro-nexus-knowledge` 中按如下结构落地：

```text
enviro-nexus-knowledge/
  README.md
  pyproject.toml
  .env.example
  docker-compose.yml
  alembic.ini
  alembic/
    env.py
    versions/
  app/
    main.py
    api/
      routes/
        health.py
        factor_query.py
        method_cards.py
    core/
      normalizer.py
      factor_matcher.py
      answer_builder.py
      evidence_builder.py
    db/
      session.py
      models.py
      repositories.py
    schemas/
      method_card.py
      query.py
      response.py
    services/
      query_service.py
      import_service.py
    settings.py
  data/
    seed/
      source_documents.json
      factor_aliases.json
      method_cards/
        gas_smoke_blackness_hj1287_2023.json
        gas_thc_methane_nmhc_hj1332_2023.json
        water_permanganate_index_hj1445_2026.json
        water_ph_hj1147_2020.json
        water_colority_hj1182_2021.json
      sample_queries.json
    backups/
  docs/
    api-contract.md
    method-card-schema.md
    db-design.md
    data-entry-guide.md
  tests/
    unit/
      test_normalizer.py
      test_factor_matcher.py
      test_answer_builder.py
      test_method_card_schema.py
    integration/
      test_factor_query_api.py
      test_seed_import.py
```

## 7. 数据模型设计

### 7.1 MethodCard JSON 结构

POC 阶段沿用 PRD 中的 MethodCard v0.1，并补充几个对知识库底座更实用的字段。核心结构如下：

```json
{
  "schema_version": "method_card.v0.1",
  "card_id": "water_ph_hj1147_2020",
  "card_version": 1,
  "identity": {
    "category": "水质",
    "factor": "pH 值",
    "factors": [
      {
        "name": "pH 值",
        "aliases": ["pH", "PH", "酸碱度", "pH值"]
      }
    ],
    "aliases": ["pH", "PH", "酸碱度", "pH值"],
    "standard_code": "HJ 1147-2020",
    "standard_name": "水质 pH 值的测定 电极法",
    "method_name": "电极法"
  },
  "applicability": {
    "sample_types": ["地表水", "地下水", "生活污水", "工业废水"],
    "field_or_lab": "现场或实验室",
    "scope_summary": "适用于地表水、地下水、生活污水和工业废水中 pH 值的测定，测定范围为 0～14。"
  },
  "measurement": {
    "principle_summary": "通过测量由参比电极和氢离子指示电极组成的测量电池电动势，直接读取 pH 值。",
    "detection_limit": null,
    "lower_limit": null,
    "upper_limit": "0～14",
    "result_unit": "pH 单位"
  },
  "requirements": [
    {
      "type": "sample_collection",
      "title": "样品采集与测定时效",
      "content": "样品可现场测定；实验室测定时，采样瓶应充满并立即密封，2 h 内完成测定。",
      "required": true,
      "evidence_ids": ["ev_sample_001"]
    }
  ],
  "qa_qc": [
    {
      "title": "仪器校准",
      "content": "每批样品测定前应对仪器进行校准；样品 pH 值变化较大或监测场地变化时应重新校准。",
      "evidence_ids": ["ev_qc_001"]
    }
  ],
  "answer_template": {
    "short_answer": "pH 值可采用 HJ 1147-2020 电极法测定。",
    "key_points": [
      "适用于地表水、地下水、生活污水和工业废水。",
      "可现场测定，也可采样后 2 h 内实验室测定。",
      "结果保留小数点后 1 位，并注明样品测定温度。"
    ]
  },
  "source_document": {
    "doc_id": "doc_hj1147_2020",
    "source_type": "standard",
    "title": "水质 pH 值的测定 电极法",
    "standard_code": "HJ 1147-2020",
    "file_path": "files/poc-files/水质 pH的测定 电极法 HJ 1147-2020.pdf",
    "status": "active",
    "import_mode": "manual_poc"
  },
  "evidence_refs": [
    {
      "evidence_id": "ev_sample_001",
      "field_path": "requirements[0].content",
      "evidence_role": "sample_requirement_basis",
      "source_title": "HJ 1147-2020",
      "section": "7 样品",
      "page": 3,
      "summary": "标准规定样品可现场测定，或采样后密封并在 2 h 内完成测定。"
    }
  ],
  "governance": {
    "review_status": "approved",
    "answer_visibility": "enabled",
    "reviewer": "manual",
    "updated_at": "2026-06-02"
  },
  "change_log": [
    {
      "version": 1,
      "change_type": "created",
      "change_note": "POC 首版方法卡"
    }
  ],
  "extensions": {}
}
```

字段设计说明：

| 字段 | 作用 | POC 要求 |
| --- | --- | --- |
| `schema_version` | 控制 MethodCard 结构版本 | 固定为 `method_card.v0.1` |
| `card_id` | 方法卡唯一标识 | 全局唯一，不随标题变化 |
| `card_version` | 方法卡内容版本 | 首版为 1，修改递增 |
| `identity.factor` | 展示标题 | 单因子卡写因子名，多因子卡写组合标题 |
| `identity.factors` | 结构化因子列表 | 每个因子单独维护 `name` 和 `aliases`，多因子方法卡必填 |
| `identity.aliases` | 方法卡级别别名 | 兼容 POC 查询；后续任务单解析优先使用 `identity.factors` |
| `applicability` | 适用范围 | 回答必需 |
| `measurement` | 方法原理、检出限、测定范围、单位 | POC 推荐必填，确无内容时为 `null` |
| `requirements` | 样品、保存、仪器、干扰、注意事项等要求 | 至少 1 条 |
| `qa_qc` | 质量保证和质量控制 | 至少 1 条 |
| `answer_template` | 标准化回答模板 | 因子查询接口直接使用 |
| `source_document` | 来源文件信息 | 必填 |
| `evidence_refs` | 依据定位 | 每个关键回答点至少关联 1 条依据 |
| `governance` | 审核和可见性 | 只有 `approved + enabled` 才可对外回答 |
| `change_log` | 方法卡变更记录 | 必填 |
| `extensions` | 后续扩展字段 | POC 保留为空对象 |

`requirements.type` 在 POC 阶段固定为以下枚举，禁止自由填写：

| 枚举值 | 含义 | 展示归类 |
| --- | --- | --- |
| `sample_collection` | 样品采集 | 样品要求 |
| `sample_preservation` | 样品保存 | 样品要求 |
| `instrument` | 仪器设备 | 仪器要求 |
| `interference` | 干扰与消除 | 干扰说明 |
| `analysis_step` | 分析步骤 | 方法步骤 |
| `result_expression` | 结果表示 | 结果表示 |
| `field_condition` | 现场条件 | 现场要求 |
| `safety_note` | 安全注意 | 安全提示 |
| `other` | 其他 | 其他要求 |

多因子方法卡示例：

```json
{
  "identity": {
    "category": "固定污染源废气",
    "factor": "总烃、甲烷、非甲烷总烃",
    "factors": [
      {
        "name": "总烃",
        "aliases": ["总烃", "THC"]
      },
      {
        "name": "甲烷",
        "aliases": ["甲烷", "CH4"]
      },
      {
        "name": "非甲烷总烃",
        "aliases": ["非甲烷总烃", "NMHC", "非甲烷烃"]
      }
    ],
    "aliases": ["总烃", "THC", "甲烷", "CH4", "非甲烷总烃", "NMHC", "非甲烷烃"],
    "standard_code": "HJ 1332-2023",
    "standard_name": "固定污染源废气 总烃、甲烷和非甲烷总烃的测定 便携式气相色谱-氢火焰离子化检测器法",
    "method_name": "便携式气相色谱-氢火焰离子化检测器法"
  }
}
```

### 7.2 PostgreSQL 表设计

#### 7.2.1 `method_cards`

保存 MethodCard 运行态数据。

迁移顺序要求：先创建 `source_documents`，再创建 `method_cards`，最后创建依赖方法卡的 `factor_aliases`。

```sql
CREATE TABLE method_cards (
  card_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  card_version INTEGER NOT NULL,
  category TEXT NOT NULL,
  factor TEXT NOT NULL,
  standard_code TEXT NOT NULL,
  standard_name TEXT NOT NULL,
  method_name TEXT NOT NULL,
  review_status TEXT NOT NULL CHECK (review_status IN ('draft', 'reviewing', 'approved', 'rejected')),
  answer_visibility TEXT NOT NULL CHECK (answer_visibility IN ('enabled', 'disabled')),
  card_json JSONB NOT NULL,
  source_doc_id TEXT NOT NULL REFERENCES source_documents(doc_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

索引：

```sql
CREATE INDEX idx_method_cards_factor ON method_cards (factor);
CREATE INDEX idx_method_cards_standard_code ON method_cards (standard_code);
CREATE INDEX idx_method_cards_category ON method_cards (category);
CREATE INDEX idx_method_cards_review_visibility ON method_cards (review_status, answer_visibility);
CREATE INDEX idx_method_cards_card_json_gin ON method_cards USING GIN (card_json);
```

设计理由：

1. `card_json` 保存完整方法卡，适合后续字段演进。
2. `factor`、`standard_code`、`review_status` 等稳定字段拆出来，避免每次查询都深入 JSON。
3. JSONB GIN 索引用于后续扩展 JSON 内字段检索。
4. `source_doc_id` 使用外键约束，确保每张方法卡都能追溯到已登记来源文件。
5. `review_status`、`answer_visibility` 使用 `CHECK` 约束，避免运行态出现不可解释状态。

#### 7.2.2 `factor_aliases`

保存别名到方法卡的映射。

```sql
CREATE TABLE factor_aliases (
  id BIGSERIAL PRIMARY KEY,
  alias TEXT NOT NULL,
  normalized_alias TEXT NOT NULL,
  factor TEXT NOT NULL,
  card_id TEXT NOT NULL REFERENCES method_cards(card_id),
  priority INTEGER NOT NULL DEFAULT 100,
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (normalized_alias, card_id)
);
```

索引：

```sql
CREATE INDEX idx_factor_aliases_normalized_alias ON factor_aliases (normalized_alias);
CREATE INDEX idx_factor_aliases_card_id ON factor_aliases (card_id);
CREATE INDEX idx_factor_aliases_enabled_priority ON factor_aliases (enabled, priority);
```

优先级规则：

| `priority` | 含义 | 示例 |
| --- | --- | --- |
| 10 | 标准主名称 | `pH 值`、`色度` |
| 20 | 常用缩写 | `pH`、`THC`、`NMHC`、`CODMn` |
| 30 | 业务俗称 | `酸碱度`、`林格曼黑度`、`耗氧量` |
| 50 | 宽泛关键词 | `颜色`、`黑烟` |

#### 7.2.3 `source_documents`

保存标准文件登记信息。

```sql
CREATE TABLE source_documents (
  doc_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  title TEXT NOT NULL,
  standard_code TEXT NOT NULL,
  file_path TEXT NOT NULL,
  status TEXT NOT NULL,
  checksum_sha256 TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`metadata` 建议保存：

```json
{
  "publish_date": "2021-06-03",
  "effective_date": "2021-09-15",
  "category": "水质",
  "pages": 6,
  "manual_extract_status": "completed"
}
```

#### 7.2.4 `knowledge_import_batches`

记录 seed 导入批次，便于排查和回滚。

```sql
CREATE TABLE knowledge_import_batches (
  batch_id TEXT PRIMARY KEY,
  import_mode TEXT NOT NULL,
  seed_path TEXT NOT NULL,
  cards_count INTEGER NOT NULL,
  aliases_count INTEGER NOT NULL,
  status TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  message TEXT
);
```

## 8. 首批 MethodCard 内容设计

### 8.1 烟气黑度 HJ 1287-2023

| 字段 | 设计内容 |
| --- | --- |
| `card_id` | `gas_smoke_blackness_hj1287_2023` |
| `factor` | 烟气黑度 |
| `aliases` | 烟气黑度、林格曼黑度、林格曼级数、黑烟、烟羽黑度 |
| `category` | 固定污染源废气 |
| `field_or_lab` | 现场观测 |
| `scope_summary` | 适用于固定污染源排放的灰色或黑色烟气在排放口处黑度的测定，不适用于其他颜色烟气。 |
| `principle_summary` | 使用林格曼望远镜在适当位置观测烟羽，将烟气黑度与内置林格曼黑度图比较，确定黑度等级。 |
| `requirements` | 白天光照充足；不适宜雨雪、雾、严重阴霾和大风条件；连续观测 30 min；一般每 15 s 观测 1 次；出现 5 级时停止观测并记录。 |
| `qa_qc` | 观测人员应经培训，视力和色觉正常；林格曼望远镜首次使用或维修后应核查图误差。 |

### 8.2 总烃、甲烷、非甲烷总烃 HJ 1332-2023

| 字段 | 设计内容 |
| --- | --- |
| `card_id` | `gas_thc_methane_nmhc_hj1332_2023` |
| `factor` | 总烃、甲烷、非甲烷总烃 |
| `factors` | 总烃：总烃、THC；甲烷：甲烷、CH4；非甲烷总烃：非甲烷总烃、NMHC、非甲烷烃 |
| `aliases` | 总烃、THC、甲烷、CH4、非甲烷总烃、NMHC、非甲烷烃 |
| `category` | 固定污染源废气 |
| `field_or_lab` | 现场仪器测定 |
| `scope_summary` | 适用于固定污染源有组织排放废气中总烃、甲烷和非甲烷总烃的测定。 |
| `measurement` | 总烃和甲烷检出限均为 0.2 mg/m3，测定下限均为 0.8 mg/m3；非甲烷总烃由总烃与甲烷差值计算。 |
| `requirements` | 颗粒物、水分冷凝、氧气可能干扰；采样管和伴热管温度控制在 120 ℃±5 ℃；连续采样测定 5 min～15 min，至少 5 个有效数据取平均。 |
| `qa_qc` | 测定前后核查示值误差、系统偏差；仪器长期未使用或每半年至少核查零点漂移和量程漂移。 |

### 8.3 高锰酸盐指数 HJ 1445-2026

| 字段 | 设计内容 |
| --- | --- |
| `card_id` | `water_permanganate_index_hj1445_2026` |
| `factor` | 高锰酸盐指数 |
| `aliases` | 高锰酸盐指数、耗氧量、CODMn、COD_Mn、IMn |
| `category` | 水质 |
| `field_or_lab` | 实验室分析 |
| `scope_summary` | 适用于地表水和地下水中氯离子浓度小于等于 300 mg/L 的高锰酸盐指数测定。 |
| `measurement` | 检出限 0.4 mg/L，测定下限 1.6 mg/L，测定上限 4.5 mg/L，以 O2 计。 |
| `requirements` | 样品 6 h 内完成分析；不能立即分析时，酸化至 pH≤2，4 ℃以下冷藏，48 h 内测定。 |
| `qa_qc` | 每批至少 2 次空白试验；每 20 个或每批次至少 1 个平行样和 1 个有证标准样品。 |

### 8.4 pH 值 HJ 1147-2020

| 字段 | 设计内容 |
| --- | --- |
| `card_id` | `water_ph_hj1147_2020` |
| `factor` | pH 值 |
| `aliases` | pH、PH、pH值、酸碱度 |
| `category` | 水质 |
| `field_or_lab` | 现场或实验室 |
| `scope_summary` | 适用于地表水、地下水、生活污水和工业废水中 pH 值的测定，测定范围 0～14。 |
| `principle_summary` | 通过测量电池电动势直接读取 pH 值。 |
| `requirements` | 可现场测定；实验室测定时采样瓶应充满并立即密封，2 h 内完成测定。 |
| `qa_qc` | 每批样品测定前校准；每 20 个样品或每批次分析有证标准样品和平行样。 |

### 8.5 色度 HJ 1182-2021

| 字段 | 设计内容 |
| --- | --- |
| `card_id` | `water_colority_hj1182_2021` |
| `factor` | 色度 |
| `aliases` | 色度、水色度、颜色、色度倍数 |
| `category` | 水质 |
| `field_or_lab` | 实验室分析 |
| `scope_summary` | 适用于生活污水和工业废水色度的测定，方法检出限和测定下限为 2 倍。 |
| `principle_summary` | 将样品稀释至与水相比无视觉感官区别，用稀释总体积与原体积的比表达颜色强度。 |
| `requirements` | 样品 4 ℃以下冷藏、避光保存，24 h 内测定；可生化性差样品可冷藏保存 15 d；测定时需描述颜色特征并测 pH。 |
| `qa_qc` | 定期使用色觉检查图对检测人员进行色觉检查，正确率应达到 100%。 |

## 9. 数据导入流程设计

### 9.1 总流程

```mermaid
flowchart TD
  A["登记 source_documents"] --> B["人工阅读标准 PDF"]
  B --> C["按字段整理 MethodCard 草稿"]
  C --> D["补充 evidence_refs"]
  D --> E["生成 factor_aliases"]
  E --> F["Pydantic Schema 校验"]
  F --> G["写入 seed JSON"]
  G --> H["执行 import 命令"]
  H --> I["写入 PostgreSQL"]
  I --> J["运行 sample_queries 测试"]
  J --> K["冻结 POC 数据版本"]
```

### 9.2 每一步详细设计

#### 步骤 1：资料登记

输入：`files/poc-files/` 下 5 个 PDF 文件。

输出：`data/seed/source_documents.json`。

每个标准登记：

```json
{
  "doc_id": "doc_hj1182_2021",
  "source_type": "standard",
  "title": "水质 色度的测定 稀释倍数法",
  "standard_code": "HJ 1182-2021",
  "file_path": "files/poc-files/水质 色度的测定 稀释倍数法 HJ 1182-2021.pdf",
  "status": "active",
  "metadata": {
    "category": "水质",
    "manual_extract_status": "completed"
  }
}
```

校验规则：

1. `doc_id` 不重复。
2. `file_path` 指向的本地文件存在。
3. `standard_code` 能从文件名或首页识别。
4. `status` POC 只允许 `active`、`draft`、`superseded`。

#### 步骤 2：方法卡人工结构化

输入：PDF 关键章节。

输出：`data/seed/method_cards/{card_id}.json`。

每张卡必须提取：

1. 标准身份：类别、展示因子标题、结构化因子列表、标准编号、标准名称、方法名称。
2. 适用范围：样品类型、现场/实验室、范围摘要。
3. 方法测定信息：方法原理、检出限、测定下限、测定上限、结果单位。
4. 关键要求：样品保存、采样、仪器、干扰、分析步骤、注意事项。
5. 质量控制：空白、平行样、标准样品、仪器校准或人员要求。
6. 回答模板：短回答和关键点。
7. 依据定位：每个关键回答点至少一个 `evidence_ref`。

#### 步骤 3：依据映射

每个 `evidence_ref` 不保存长篇标准原文，只保存定位和摘要。

推荐结构：

```json
{
  "evidence_id": "ev_scope_001",
  "field_path": "applicability.scope_summary",
  "evidence_role": "applicability_basis",
  "source_title": "HJ 1182-2021",
  "section": "1 适用范围",
  "page": 1,
  "summary": "该标准规定稀释倍数法适用于生活污水和工业废水色度测定。"
}
```

设计原因：

1. `field_path` 能说明依据支持哪个结构化字段。
2. `section + page` 能让人工回查标准。
3. `summary` 用于接口展示，避免返回标准全文。

#### 步骤 4：别名生成

输出：`data/seed/factor_aliases.json`。

POC 首批别名：

| 因子 | 别名 |
| --- | --- |
| 烟气黑度 | 烟气黑度、林格曼黑度、林格曼级数、黑烟、烟羽黑度 |
| 总烃、甲烷、非甲烷总烃 | 总烃、THC、甲烷、CH4、非甲烷总烃、NMHC、非甲烷烃 |
| 高锰酸盐指数 | 高锰酸盐指数、耗氧量、CODMn、COD_Mn、IMn |
| pH 值 | pH、PH、pH值、酸碱度 |
| 色度 | 色度、水色度、颜色、色度倍数 |

别名设计原则：

1. 标准名称优先。
2. 业务常用简称必须覆盖。
3. 容易误伤的宽泛词降低优先级，例如 `颜色`。
4. 多因子同卡时允许多个别名指向同一个 `card_id`。

#### 步骤 5：Schema 校验

导入前使用 Pydantic 做强校验。

校验项：

1. `card_id` 格式：小写字母、数字、下划线。
2. `schema_version` 必须等于 `method_card.v0.1`。
3. `card_version` 大于等于 1。
4. `identity.factor` 不为空。
5. `identity.factors` 不为空，每个元素必须包含 `name` 和非空 `aliases`。
6. `identity.aliases` 不为空，且应覆盖 `identity.factors[].aliases`。
7. `source_document.doc_id` 必须存在于 `source_documents.json`。
8. `requirements` 不为空，且 `requirements[].type` 必须属于固定枚举。
9. `qa_qc` 不为空。
10. `answer_template.short_answer` 不为空。
11. `evidence_refs.evidence_id` 不重复。
12. `requirements[].evidence_ids` 指向存在的 `evidence_refs`。

#### 步骤 6：幂等导入

导入命令设计：

```bash
uv run python -m app.services.import_service --seed data/seed --mode upsert
```

导入行为：

1. 读取 `source_documents.json` 并 upsert 到 `source_documents`。
2. 读取 `method_cards/*.json`，校验后 upsert 到 `method_cards`。
3. 读取 `factor_aliases.json`，校验后 upsert 到 `factor_aliases`。
4. 记录 `knowledge_import_batches`。
5. 如果任意文件校验失败，整个事务回滚。

#### 步骤 7：导入后验证

运行：

```bash
uv run pytest tests/integration/test_seed_import.py -v
uv run pytest tests/integration/test_factor_query_api.py -v
```

验证内容：

1. 数据库中有 5 张可见方法卡。
2. 每张方法卡 `review_status=approved` 且 `answer_visibility=enabled`。
3. 每张方法卡至少有 3 个别名。
4. 每张方法卡至少有 3 条依据。
5. 固定演示问题均能命中。

## 10. 查询流程设计

### 10.1 查询链路

```mermaid
sequenceDiagram
  participant U as User/API Consumer
  participant API as FastAPI Route
  participant QS as QueryService
  participant N as Normalizer
  participant FM as FactorMatcher
  participant DB as PostgreSQL
  participant AB as AnswerBuilder
  participant EB as EvidenceBuilder

  U->>API: POST /api/v1/factors/query
  API->>QS: query text
  QS->>N: normalize(query)
  N-->>QS: normalized query
  QS->>FM: match(normalized query)
  FM->>DB: find aliases and cards
  DB-->>FM: candidates
  FM-->>QS: best match or unmatched
  QS->>DB: load method card
  DB-->>QS: MethodCard JSONB
  QS->>AB: build answer
  AB->>EB: attach evidence refs
  EB-->>AB: evidence list
  AB-->>QS: structured answer
  QS-->>API: response model
  API-->>U: JSON response
```

### 10.2 输入标准化

`normalizer.py` 负责把用户输入转换成可匹配文本。

规则：

1. 去除首尾空白。
2. 全角转半角。
3. 英文统一小写，但保留原始输入用于展示。
4. 移除常见问句词：`怎么测`、`用什么方法`、`标准`、`检测`、`测定`。
5. 统一符号：`COD-Mn`、`COD_Mn`、`COD Mn` 归一为 `codmn`。
6. `pH`、`PH`、`ph` 归一为 `ph`。
7. 去除无意义标点。

示例：

| 原始输入 | 标准化结果 |
| --- | --- |
| `pH 怎么测？` | `ph` |
| `非甲烷总烃用哪个标准` | `非甲烷总烃` |
| `COD-Mn 检测方法` | `codmn` |
| `水样颜色怎么报结果` | `水样颜色` |

### 10.3 匹配策略

POC 使用确定性匹配，不使用大模型。

匹配优先级：

1. `normalized_query == normalized_alias`，置信度 `1.00`。
2. `normalized_query` 包含完整 `normalized_alias`，置信度 `0.90`。
3. `normalized_alias` 包含在去问句后的关键词中，置信度 `0.80`。
4. 多个别名命中同一张卡，按最高置信度返回。
5. 多张卡同分命中，返回 `matched=false` 或返回候选，并给出歧义提示。

POC 不做模糊拼音和编辑距离，避免误命中。

### 10.4 歧义处理

歧义示例：

| 输入 | 风险 | 处理 |
| --- | --- | --- |
| `颜色怎么测` | 可能指色度，也可能是业务泛问 | 命中色度，但 `warnings` 提示“按色度理解，请确认检测因子” |
| `烃类怎么测` | 可能是总烃、甲烷、非甲烷总烃 | 返回 HJ 1332 卡，并提示“已按总烃/甲烷/非甲烷总烃理解” |
| `COD 怎么测` | 当前 POC 只有 CODMn，不覆盖 CODCr | 不直接命中高锰酸盐指数，返回未收录或候选提示 |

原则：宁可未命中，也不错误命中。

## 11. 回答组装设计

`answer_builder.py` 使用 MethodCard 中的 `answer_template`、`applicability`、`measurement`、`requirements`、`qa_qc` 组装响应。

### 11.1 回答字段

```json
{
  "summary": "pH 值可采用 HJ 1147-2020 电极法测定。",
  "standard_code": "HJ 1147-2020",
  "standard_name": "水质 pH 值的测定 电极法",
  "method_name": "电极法",
  "applicability": "适用于地表水、地下水、生活污水和工业废水中 pH 值的测定，测定范围为 0～14。",
  "measurement": {
    "detection_limit": null,
    "lower_limit": null,
    "upper_limit": "0～14",
    "result_unit": "pH 单位"
  },
  "requirements": [
    {
      "type": "sample",
      "title": "样品采集与测定时效",
      "content": "样品可现场测定；实验室测定时，采样瓶应充满并立即密封，2 h 内完成测定。"
    }
  ],
  "qa_qc": [
    {
      "title": "仪器校准",
      "content": "每批样品测定前应对仪器进行校准。"
    }
  ],
  "evidence_refs": [
    {
      "source_title": "HJ 1147-2020",
      "section": "7 样品",
      "page": 3,
      "summary": "标准规定样品可现场测定，或采样后密封并在 2 h 内完成测定。"
    }
  ]
}
```

### 11.2 回答生成规则

1. `summary` 优先使用 `answer_template.short_answer`。
2. `applicability` 来自 `applicability.scope_summary`。
3. `requirements` 只返回 POC 展示需要的关键要求，不返回所有实验步骤。
4. `qa_qc` 单独返回，避免混入样品要求。
5. `evidence_refs` 只返回与本次回答字段相关的依据。
6. 如果 `governance.review_status != approved` 或 `answer_visibility != enabled`，不对外返回该卡。

## 12. API 设计

接口路径统一带 `/api/v1`。

### 12.1 健康检查

```http
GET /api/v1/health
```

响应：

```json
{
  "status": "ok",
  "service": "enviro-nexus-knowledge",
  "api_version": "v1",
  "database": "ok"
}
```

### 12.2 因子查询

```http
POST /api/v1/factors/query
```

请求：

```json
{
  "query": "pH 怎么测？"
}
```

成功命中响应：

```json
{
  "api_version": "v1",
  "matched": true,
  "factor": "pH 值",
  "matched_alias": "pH",
  "match_confidence": 1.0,
  "card_id": "water_ph_hj1147_2020",
  "answer": {
    "summary": "pH 值可采用 HJ 1147-2020 电极法测定。",
    "standard_code": "HJ 1147-2020",
    "standard_name": "水质 pH 值的测定 电极法",
    "method_name": "电极法",
    "applicability": "适用于地表水、地下水、生活污水和工业废水中 pH 值的测定，测定范围为 0～14。",
    "requirements": [
      {
        "type": "sample",
        "title": "样品采集与测定时效",
        "content": "样品可现场测定；实验室测定时，采样瓶应充满并立即密封，2 h 内完成测定。"
      }
    ],
    "evidence_refs": [
      {
        "source_title": "HJ 1147-2020",
        "section": "7 样品",
        "page": 3,
        "summary": "标准规定样品可现场测定，或采样后密封并在 2 h 内完成测定。"
      }
    ]
  },
  "warnings": []
}
```

未命中响应：

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

### 12.3 方法卡详情

```http
GET /api/v1/method-cards/{card_id}
```

接口定位：POC 调试接口。

响应：返回完整 MethodCard JSON，包括治理字段、变更记录、来源文件路径和扩展字段。

规则：

1. 不存在时返回 404。
2. 存在但未启用展示时返回 404 或 403，POC 推荐 404，避免消费者误用草稿卡。
3. 返回字段保持 MethodCard 原始结构，方便后端和前端调试。
4. 前端 POC 可以临时读取该接口，但不得把完整内部结构作为长期展示契约。

后续正式展示接口预留：

```http
GET /api/v1/method-cards/{card_id}/public
```

`/public` 只返回前端展示所需字段，例如标准编号、标准名称、方法名称、适用范围、关键要求、质控要求和依据来源，不返回 `governance`、`change_log`、内部文件路径等治理字段。POC 阶段不实现该接口，只在契约中提前说明边界。

### 12.4 错误码设计

| 场景 | HTTP 状态码 | 响应说明 |
| --- | --- | --- |
| 请求体缺少 `query` | 422 | FastAPI 参数校验失败 |
| `query` 为空字符串 | 400 | 返回业务错误 `empty_query` |
| 数据库不可用 | 503 | 返回 `database_unavailable` |
| 方法卡不存在 | 404 | 返回 `method_card_not_found` |
| 服务内部异常 | 500 | 返回 `internal_error`，日志记录详细异常 |

## 13. Docker 与本地环境设计

### 13.1 PostgreSQL 容器

推荐使用 Docker Compose 启动数据库：

```yaml
services:
  postgres:
    image: postgres:16
    container_name: enviro-nexus-knowledge-postgres
    environment:
      POSTGRES_DB: enviro_nexus_knowledge
      POSTGRES_USER: enviro_nexus
      POSTGRES_PASSWORD: enviro_nexus_dev
    ports:
      - "15432:5432"
    volumes:
      - enviro_nexus_knowledge_pgdata:/var/lib/postgresql/data
      - ./data/backups:/backups

volumes:
  enviro_nexus_knowledge_pgdata:
```

设计要点：

1. PostgreSQL 数据目录使用 named volume，不直接 bind mount 到 Windows 本地目录。
2. `data/seed` 作为项目数据源，由应用导入，不直接挂到 PostgreSQL 初始化目录。
3. `data/backups` 用于导出 SQL 或自定义格式备份，便于迁移。
4. 本地端口使用 `15432`，降低与本机 PostgreSQL 冲突概率。

### 13.2 环境变量

`.env.example`：

```env
APP_ENV=local
API_VERSION=v1
DATABASE_URL=postgresql+psycopg://enviro_nexus:enviro_nexus_dev@localhost:15432/enviro_nexus_knowledge
LOG_LEVEL=INFO
```

### 13.3 常用命令

```bash
docker compose up -d postgres
uv sync
uv run alembic upgrade head
uv run python -m app.services.import_service --seed data/seed --mode upsert
uv run uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
uv run pytest -v
```

## 14. 数据迁移与版本管理

### 14.1 表结构迁移

使用 Alembic 管理表结构：

1. 每次新增或修改表字段都生成 migration。
2. migration 文件提交到仓库。
3. 本地和演示环境统一执行 `alembic upgrade head`。

### 14.2 MethodCard 内容版本

MethodCard 内容通过以下字段控制：

| 字段 | 用途 |
| --- | --- |
| `schema_version` | 控制结构版本，例如 `method_card.v0.1` |
| `card_version` | 控制某张方法卡内容版本 |
| `change_log` | 记录每次内容变更原因 |
| `governance.updated_at` | 记录最近更新日期 |

升级策略：

1. POC 期间固定 `schema_version=method_card.v0.1`。
2. 修正某张卡内容时只递增 `card_version`。
3. 后续新增大字段或调整结构时再升级 `schema_version`。

### 14.3 数据备份与迁移

备份命令示例：

```bash
docker exec enviro-nexus-knowledge-postgres pg_dump \
  -U enviro_nexus \
  -d enviro_nexus_knowledge \
  -F c \
  -f /backups/enviro_nexus_knowledge_poc.dump
```

迁移策略：

1. 表结构靠 Alembic。
2. 基础知识数据靠 seed JSON。
3. 运行态数据库可通过 `pg_dump` 备份。
4. 后续环境迁移时，优先执行 migration，再导入 seed，再恢复必要运行态数据。

## 15. 测试设计

### 15.1 单元测试

| 测试文件 | 覆盖内容 |
| --- | --- |
| `tests/unit/test_normalizer.py` | pH、CODMn、NMHC、中文问句归一化 |
| `tests/unit/test_factor_matcher.py` | 精确匹配、包含匹配、歧义匹配、未命中 |
| `tests/unit/test_answer_builder.py` | MethodCard 到结构化回答转换 |
| `tests/unit/test_method_card_schema.py` | 5 张 seed 方法卡 Schema 校验 |

### 15.2 集成测试

| 测试文件 | 覆盖内容 |
| --- | --- |
| `tests/integration/test_seed_import.py` | source、card、alias 幂等导入 |
| `tests/integration/test_factor_query_api.py` | `/api/v1/factors/query` 命中和未命中 |
| `tests/integration/test_method_card_api.py` | `/api/v1/method-cards/{card_id}` 查询 |
| `tests/integration/test_health_api.py` | 服务和数据库健康检查 |

### 15.3 演示问题测试集

`data/seed/sample_queries.json` 建议包含：

```json
[
  {
    "query": "pH 怎么测？",
    "expected_card_id": "water_ph_hj1147_2020"
  },
  {
    "query": "水样酸碱度用什么标准？",
    "expected_card_id": "water_ph_hj1147_2020"
  },
  {
    "query": "色度怎么测？",
    "expected_card_id": "water_colority_hj1182_2021"
  },
  {
    "query": "CODMn 用哪个方法？",
    "expected_card_id": "water_permanganate_index_hj1445_2026"
  },
  {
    "query": "耗氧量样品怎么保存？",
    "expected_card_id": "water_permanganate_index_hj1445_2026"
  },
  {
    "query": "烟气黑度如何测定？",
    "expected_card_id": "gas_smoke_blackness_hj1287_2023"
  },
  {
    "query": "林格曼黑度观测要求",
    "expected_card_id": "gas_smoke_blackness_hj1287_2023"
  },
  {
    "query": "非甲烷总烃用哪个标准？",
    "expected_card_id": "gas_thc_methane_nmhc_hj1332_2023"
  },
  {
    "query": "NMHC 怎么测？",
    "expected_card_id": "gas_thc_methane_nmhc_hj1332_2023"
  },
  {
    "query": "COD 怎么测？",
    "expected_card_id": null,
    "expected_matched": false
  }
]
```

### 15.4 验收测试命令

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run python -m app.services.import_service --seed data/seed --mode upsert
uv run pytest -v
curl http://localhost:8010/api/v1/health
curl -X POST http://localhost:8010/api/v1/factors/query \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"pH 怎么测？\"}"
```

## 16. 日志与可观测性设计

POC 阶段日志先保持简单，但必须能排查查询问题。

### 16.1 日志字段

每次查询记录：

1. `request_id`
2. `raw_query`
3. `normalized_query`
4. `matched`
5. `matched_alias`
6. `card_id`
7. `match_confidence`
8. `warnings`
9. `duration_ms`

### 16.2 不落库的内容

POC 阶段不保存用户身份、敏感业务单据、原始任务单文件。日志只用于本地调试。

## 17. 安全与治理设计

1. 数据库密码只放 `.env`，不写入 README 或代码。
2. MethodCard 回答明确定位为“标准方法结构化摘要”，不替代标准全文。
3. `review_status=approved` 且 `answer_visibility=enabled` 才能对外返回。
4. 每条关键回答必须可追溯到 `source_document + section + page`。
5. seed 数据修改必须同步更新 `change_log`。
6. 文件路径使用项目相对路径，避免绑定个人机器路径。

## 18. 开工前冻结项

开工前固定以下约束，开发过程中不再反复调整基础口径：

1. `card_id` 命名统一使用 `gas_` 和 `water_`，固定污染源废气不用 `air_`。
2. MethodCard Schema 固定为 `method_card.v0.1`。
3. MethodCard 保留 `identity.factor` 作为展示标题，同时使用 `identity.factors` 支撑多因子方法卡。
4. `requirements.type` 固定使用 POC 枚举，不自由填写。
5. PostgreSQL 表结构按本文 DDL 和约束执行，`source_doc_id` 使用外键，状态字段使用 `CHECK`。
6. 开发顺序先用 `water_ph_hj1147_2020` 一张卡打穿纵向闭环，再补其余 4 张卡。
7. 因子查询接口先只做 `POST /api/v1/factors/query`。
8. `GET /api/v1/method-cards/{card_id}` 先作为 POC 调试接口，不作为前端长期展示契约。
9. `COD` 不自动命中 `CODMn`。
10. 每个 answer 字段必须能追到 `evidence_refs`。
11. seed JSON 是知识数据源，PostgreSQL 是运行态数据库。
12. POC 不引入大模型、不引入向量检索、不做自动 PDF 抽取。

## 19. POC 开发步骤

### Day 0：工程和数据库底座

目标：知识服务可启动，数据库可连接。

产出：

1. 初始化 `enviro-nexus-knowledge` Python 工程。
2. 增加 `docker-compose.yml` 启动 PostgreSQL。
3. 增加 `.env.example`。
4. 增加 SQLAlchemy 连接和 Alembic。
5. 按 `source_documents`、`method_cards`、`factor_aliases`、`knowledge_import_batches` 顺序创建表。
6. 实现 `/api/v1/health`。

验收：

1. `docker compose up -d postgres` 成功。
2. `uv run alembic upgrade head` 成功。
3. `curl /api/v1/health` 返回 `database=ok`。

### Day 1：用 pH 单卡打穿纵向闭环

目标：先用 `water_ph_hj1147_2020` 一张 MethodCard 验证工程链路，避免先陷入 5 份资料的人工整理。

产出：

1. 定义 Pydantic MethodCard 模型。
2. 编写 `source_documents.json`。
3. 编写 `water_ph_hj1147_2020.json`。
4. 编写 pH 相关 `factor_aliases.json`。
5. 实现 pH seed 幂等导入。
6. 实现最小 `normalizer.py`、`factor_matcher.py`、`answer_builder.py`、`evidence_builder.py`。
7. 实现 `POST /api/v1/factors/query` 的 pH 闭环返回。
8. 编写 pH Schema、导入、查询、依据返回测试。

验收：

1. `pytest tests/unit/test_method_card_schema.py -v` 通过。
2. `water_ph_hj1147_2020` 可导入 PostgreSQL。
3. `pH 怎么测？` 命中 `water_ph_hj1147_2020`。
4. API 返回包含 `summary`、标准编号、适用范围、关键要求和 `evidence_refs`。

### Day 2：补齐水质卡和导入能力

目标：在 pH 闭环稳定后，补充 `water_colority_hj1182_2021` 和 `water_permanganate_index_hj1445_2026`。

产出：

1. 完善 import service，支持多文件 seed 导入。
2. 完善 source/card/alias repository。
3. 编写色度 MethodCard JSON。
4. 编写高锰酸盐指数 MethodCard JSON。
5. 补充色度、高锰酸盐指数别名。
6. 实现导入事务和导入批次记录。
7. 编写 seed import 集成测试。

验收：

1. 连续执行两次导入不产生重复数据。
2. 数据库中可查询到 3 张启用水质方法卡。
3. `色度怎么测？` 命中 `water_colority_hj1182_2021`。
4. `CODMn 用哪个方法？` 命中 `water_permanganate_index_hj1445_2026`。
5. `COD 怎么测？` 不误命中 `CODMn`。

### Day 3：补齐废气卡和多因子匹配

目标：补充 `gas_smoke_blackness_hj1287_2023` 和 `gas_thc_methane_nmhc_hj1332_2023`，验证固定污染源废气和多因子方法卡设计。

产出：

1. 编写烟气黑度 MethodCard JSON。
2. 编写总烃、甲烷、非甲烷总烃 MethodCard JSON，并补齐 `identity.factors`。
3. 补充废气类别名。
4. 完善 `factor_matcher.py`，支持多因子别名命中同一张卡。
5. 完善 `query_service.py`。
6. 补充 sample queries 测试。

验收：

1. `烟气黑度如何测定？` 命中 `gas_smoke_blackness_hj1287_2023`。
2. `NMHC 怎么测？` 命中 `gas_thc_methane_nmhc_hj1332_2023`。
3. `甲烷用哪个标准？` 命中 `gas_thc_methane_nmhc_hj1332_2023`。
4. 数据库中可查询到 5 张启用方法卡。
5. 别名总数不少于 20 条。

### Day 4：API 契约与集成测试

目标：知识服务 API 可供后端或前端联调。

产出：

1. 补齐 `GET /api/v1/method-cards/{card_id}` 调试接口。
2. 冻结 `POST /api/v1/factors/query` 请求和响应结构。
3. 编写 `docs/api-contract.md`，说明方法卡详情接口是 POC 调试接口。
4. 编写 API 集成测试和 sample queries 回归测试。
5. 补充 README 启动说明。

验收：

1. OpenAPI 文档能展示接口。
2. curl 可以完成健康检查、因子查询、方法卡详情查询。
3. API 返回结构与 PRD 契约一致。
4. 前端展示字段不依赖 MethodCard 内部治理字段。

### Day 5：演示冻结和问题修正

目标：冻结 POC 数据和接口。

产出：

1. 固定 10 条演示问题。
2. 补齐缺失 warnings。
3. 检查 evidence_refs 是否完整。
4. 导出数据库备份。
5. 标记 POC 数据版本。

验收：

1. 所有测试通过。
2. 5 张方法卡全部可查。
3. 每个命中回答都有标准编号、方法名称、适用范围、关键要求、依据来源。
4. 未收录因子返回清晰提示。

## 20. 验收标准

POC 通过标准：

1. PostgreSQL 容器可通过 Docker Compose 一键启动。
2. 数据库 migration 可从空库执行成功。
3. 5 份标准资料均有对应 MethodCard。
4. 5 张 MethodCard 均可通过 Schema 校验并导入数据库。
5. 每张 MethodCard 至少有 3 个别名、3 条依据、1 条质量控制要求。
6. `/api/v1/health` 可返回服务和数据库状态。
7. `/api/v1/factors/query` 可命中首批演示问题。
8. `/api/v1/method-cards/{card_id}` 可返回完整方法卡。
9. `COD` 不误命中 `CODMn`。
10. API 返回内容可直接支撑前端结果卡片和依据列表展示。

## 21. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| PDF 自动抽取质量不稳定 | 方法卡字段可能不准确 | POC 使用人工结构化，PDF 抽取只辅助定位 |
| 因子别名误命中 | 返回错误标准方法 | 采用保守匹配策略，宽泛词降低优先级，歧义时提示或未命中 |
| `COD` 与 `CODMn` 混淆 | 业务误导风险高 | POC 明确 `COD` 不自动等同高锰酸盐指数 |
| JSONB 字段过度自由 | 后续数据质量下降 | 用 Pydantic Schema 强校验，稳定字段拆成关系列 |
| Docker 数据目录迁移困难 | 本地环境重建成本高 | PostgreSQL 数据用 named volume，seed 和 backup 用本地目录 |
| 回答缺少依据 | 知识服务可信度不足 | 验收要求每个关键回答点必须有关联 evidence |
| 标准状态变化 | 方法卡过期 | source_documents 记录状态，后续引入标准有效性复核流程 |

## 22. 后续扩展路径

POC 通过后，建议按下面顺序扩展：

1. 扩展更多水质高频因子。
2. 增加标准状态复核和方法卡审核流程。
3. 增加任务单检测因子批量识别。
4. 引入全文索引或 pgvector 做依据召回。
5. 增加半自动 PDF 抽取辅助工具。
6. 与 `enviro-nexus-api` 联调统一返回格式。
7. 与 `enviro-nexus-web` 联调展示结果卡片和依据列表。
8. 增加后台数据维护能力。

## 23. 最小可交付清单

POC 最小交付物：

1. `enviro-nexus-knowledge` 可启动服务。
2. PostgreSQL Docker Compose 配置。
3. Alembic migration。
4. MethodCard Pydantic Schema。
5. 5 张 MethodCard seed JSON。
6. source documents seed JSON。
7. factor aliases seed JSON。
8. seed import 命令。
9. 因子查询 API。
10. 方法卡详情 API。
11. 健康检查 API。
12. API 契约文档。
13. 10 条 sample queries。
14. 单元测试和集成测试。

该交付范围足够支撑第一阶段演示，也不会把复杂度提前推到大模型、自动抽取或后台管理系统上。
