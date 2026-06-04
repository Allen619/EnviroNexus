# EnviroNexus Knowledge API Contract

本文档面向 EnviroNexus 团队，说明 `enviro-nexus-knowledge` 在 POC 阶段对外稳定提供的 Knowledge API 契约。

当前契约只覆盖 `enviro-nexus-knowledge`，不包含 `enviro-nexus-api` 和 `enviro-nexus-web`。

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 服务名 | `enviro-nexus-knowledge` |
| 默认本地地址 | `http://127.0.0.1:8010` |
| API 前缀 | `/api/v1` |
| 数据来源 | PostgreSQL 中已导入的 approved + enabled MethodCard |
| Content-Type | `application/json; charset=utf-8` |

在线文档入口：

| 文档 | 地址 |
| --- | --- |
| Swagger UI | `http://127.0.0.1:8010/docs` |
| ReDoc | `http://127.0.0.1:8010/redoc` |
| OpenAPI JSON | `http://127.0.0.1:8010/openapi.json` |

## 2. 字段公开边界

公开接口只返回前端展示和后端编排所需字段。

以下内部治理字段不得通过公开接口返回：

```text
governance
change_log
extensions
source_document
file_path
metadata
evidence_id
evidence_ids
needs_pdf_check
```

`POST /api/v1/factors/query` 的 `answer` 字段也遵守上述公开边界，不返回内部治理字段和 `evidence_ids`。

`evidence_refs` 只返回：

```text
source_title
section
page
summary
```

## 3. 错误响应格式

业务错误和数据库错误使用统一结构：

```json
{
  "error_code": "database_unavailable",
  "message": "database is unavailable",
  "api_version": "v1"
}
```

请求体 schema 校验失败时，FastAPI 会返回默认 `422 Unprocessable Entity` 结构。

## 4. GET /api/v1/health

健康检查接口，用于确认服务和数据库可用性。

### 4.1 请求

```http
GET /api/v1/health
```

### 4.2 成功响应

HTTP 状态码：`200 OK`

```json
{
  "status": "ok",
  "service": "enviro-nexus-knowledge",
  "api_version": "v1",
  "database": "ok"
}
```

### 4.3 数据库不可用响应

HTTP 状态码：`503 Service Unavailable`

```json
{
  "status": "error",
  "service": "enviro-nexus-knowledge",
  "api_version": "v1",
  "database": "unavailable"
}
```

### 4.4 curl 示例

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/health"
```

## 5. POST /api/v1/factors/query

检测因子查询接口。服务会对用户输入做归一化处理，再通过 `factor_aliases` 匹配 approved + enabled MethodCard，并组装结构化回答和依据来源。

### 5.1 请求

```http
POST /api/v1/factors/query
Content-Type: application/json; charset=utf-8
```

请求体：

```json
{
  "query": "pH 怎么测？"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | string | 是 | 用户输入的检测因子或简单问题 |

### 5.2 命中响应

HTTP 状态码：`200 OK`

```json
{
  "api_version": "v1",
  "matched": true,
  "factor": "pH 值",
  "matched_alias": "pH",
  "match_confidence": 1.0,
  "card_id": "water_ph_hj1147_2020",
  "answer": {
    "summary": "pH 值可采用 HJ 1147-2020《水质 pH 值的测定 电极法》测定。",
    "standard_code": "HJ 1147-2020",
    "standard_name": "水质 pH 值的测定 电极法",
    "method_name": "电极法",
    "applicability": "适用于地表水、地下水、生活污水和工业废水中 pH 值的测定，测定范围为 0～14。",
    "measurement": {
      "principle": "通过测量由参比电极和氢离子指示电极组成的测量电池电动势，直接读取 pH 值。",
      "instrument": "酸度计、温度计或温度传感器、pH 复合电极等",
      "unit": "pH 单位",
      "range": {
        "lower": "0",
        "upper": "14",
        "unit": "pH 单位"
      }
    },
    "requirements": [
      {
        "type": "sample_collection",
        "title": "样品采集与测定时效",
        "content": "样品可现场测定；实验室测定时，采样瓶应充满并立即密封，2 h 内完成测定。"
      }
    ],
    "qa_qc": [
      {
        "title": "仪器校准",
        "content": "每批样品测定前应对仪器进行校准；样品 pH 值变化较大或监测场地变化时应重新校准。"
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

### 5.3 未命中响应

HTTP 状态码：`200 OK`

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

### 5.4 空 query 响应

HTTP 状态码：`400 Bad Request`

```json
{
  "error_code": "empty_query",
  "message": "query must not be empty",
  "api_version": "v1"
}
```

### 5.5 数据库不可用响应

HTTP 状态码：`503 Service Unavailable`

```json
{
  "error_code": "database_unavailable",
  "message": "database is unavailable",
  "api_version": "v1"
}
```

### 5.6 PowerShell 示例

推荐使用 `Invoke-RestMethod`，避免 Windows PowerShell 下 curl JSON 转义问题。

```powershell
$body = @{ query = "pH 怎么测？" } | ConvertTo-Json -Compress
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8010/api/v1/factors/query" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

验证 COD 不误命中 CODMn：

```powershell
$body = @{ query = "COD 怎么测？" } | ConvertTo-Json -Compress
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8010/api/v1/factors/query" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

预期：

```text
matched = false
card_id = null
```

验证 CODMn 命中：

```powershell
$body = @{ query = "CODMn 怎么测？" } | ConvertTo-Json -Compress
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8010/api/v1/factors/query" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

预期：

```text
matched = true
card_id = water_permanganate_index_hj1445_2026
answer.evidence_refs 非空
```

## 6. GET /api/v1/method-cards

公开方法卡列表接口。只返回 `review_status=approved` 且 `answer_visibility=enabled` 的 MethodCard。

### 6.1 请求

```http
GET /api/v1/method-cards
```

### 6.2 固定排序规则

列表接口固定按以下字段升序排序：

```text
category ASC
factor ASC
standard_code ASC
card_id ASC
```

调用方不需要自己假设数据库默认顺序，也不要依赖导入顺序。

### 6.3 成功响应

HTTP 状态码：`200 OK`

```json
{
  "api_version": "v1",
  "items": [
    {
      "card_id": "gas_smoke_blackness_hj1287_2023",
      "factor": "烟气黑度",
      "category": "固定污染源废气",
      "standard_code": "HJ 1287-2023",
      "standard_name": "固定污染源废气 烟气黑度的测定 林格曼望远镜法",
      "method_name": "林格曼望远镜法",
      "applicability": "适用于固定污染源排放的灰色或黑色烟气在排放口处黑度的测定，不适用于其他颜色烟气。"
    }
  ],
  "count": 5
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `api_version` | string | API 版本 |
| `items` | array | 公开方法卡摘要列表 |
| `count` | integer | 当前返回条数 |

`items[]` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `card_id` | string | 方法卡唯一标识 |
| `factor` | string | 检测因子展示名 |
| `category` | string | 类别 |
| `standard_code` | string | 标准编号 |
| `standard_name` | string | 标准名称 |
| `method_name` | string | 方法名称 |
| `applicability` | string | 适用范围摘要 |

### 6.4 数据库不可用响应

HTTP 状态码：`503 Service Unavailable`

```json
{
  "error_code": "database_unavailable",
  "message": "database is unavailable",
  "api_version": "v1"
}
```

### 6.5 curl 示例

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards"
```

## 7. GET /api/v1/method-cards/{card_id}/public

公开方法卡详情接口。用于前端结果卡片、详情页或后端聚合展示。

该接口只返回 approved + enabled 方法卡。如果卡不存在、未 approved 或 disabled，统一返回 404。

### 7.1 请求

```http
GET /api/v1/method-cards/{card_id}/public
```

路径参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `card_id` | string | 是 | 方法卡唯一标识 |

示例：

```http
GET /api/v1/method-cards/water_ph_hj1147_2020/public
```

### 7.2 成功响应

HTTP 状态码：`200 OK`

```json
{
  "api_version": "v1",
  "card": {
    "card_id": "water_ph_hj1147_2020",
    "factor": "pH 值",
    "category": "水质",
    "standard_code": "HJ 1147-2020",
    "standard_name": "水质 pH 值的测定 电极法",
    "method_name": "电极法",
    "applicability": "适用于地表水、地下水、生活污水和工业废水中 pH 值的测定，测定范围为 0～14。",
    "measurement": {
      "principle": "通过测量由参比电极和氢离子指示电极组成的测量电池电动势，直接读取 pH 值。",
      "instrument": "酸度计、温度计或温度传感器、pH 复合电极等",
      "unit": "pH 单位",
      "range": {
        "lower": "0",
        "upper": "14",
        "unit": "pH 单位"
      }
    },
    "requirements": [
      {
        "type": "sample_collection",
        "title": "样品采集与测定时效",
        "content": "样品可现场测定；实验室测定时，采样瓶应充满并立即密封，2 h 内完成测定。"
      }
    ],
    "qa_qc": [
      {
        "title": "仪器校准",
        "content": "每批样品测定前应对仪器进行校准；样品 pH 值变化较大或监测场地变化时应重新校准。"
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
}
```

### 7.3 card 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `card_id` | string | 方法卡唯一标识 |
| `factor` | string | 检测因子展示名 |
| `category` | string | 类别 |
| `standard_code` | string | 标准编号 |
| `standard_name` | string | 标准名称 |
| `method_name` | string | 方法名称 |
| `applicability` | string | 适用范围摘要 |
| `measurement` | object | 测定方法摘要 |
| `requirements` | array | 采样、保存、干扰、步骤、结果表示、安全等关键要求 |
| `qa_qc` | array | 质量保证和质量控制要求 |
| `evidence_refs` | array | 依据来源列表 |

`measurement` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `principle` | string | 方法原理 |
| `instrument` | string | 主要仪器设备 |
| `unit` | string 或 null | 结果单位 |
| `range` | object 或 null | 测定范围 |

`measurement.range` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `lower` | string 或 null | 下限 |
| `upper` | string 或 null | 上限 |
| `unit` | string 或 null | 范围单位 |

`requirements[]` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `type` | string | 要求类型 |
| `title` | string | 要求标题 |
| `content` | string | 要求内容 |

`qa_qc[]` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | string | 质控标题 |
| `content` | string | 质控内容 |

`evidence_refs[]` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source_title` | string | 来源标准标题或编号 |
| `section` | string | 标准章节 |
| `page` | integer 或 null | 页码 |
| `summary` | string | 依据摘要 |

### 7.4 不存在或不可公开响应

HTTP 状态码：`404 Not Found`

```json
{
  "error_code": "method_card_not_found",
  "message": "method card is not found or not public",
  "api_version": "v1"
}
```

适用场景：

```text
card_id 不存在
MethodCard 未 approved
MethodCard answer_visibility 为 disabled
```

### 7.5 数据库不可用响应

HTTP 状态码：`503 Service Unavailable`

```json
{
  "error_code": "database_unavailable",
  "message": "database is unavailable",
  "api_version": "v1"
}
```

### 7.6 curl 示例

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards/water_ph_hj1147_2020/public"
```

不存在卡：

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards/not_exists/public"
```

## 8. POC 当前公开数据

当前 POC seed 数据包含 5 张公开 MethodCard：

| card_id | factor | standard_code |
| --- | --- | --- |
| `water_ph_hj1147_2020` | pH 值 | HJ 1147-2020 |
| `water_colority_hj1182_2021` | 色度 | HJ 1182-2021 |
| `water_permanganate_index_hj1445_2026` | 高锰酸盐指数 | HJ 1445-2026 |
| `gas_smoke_blackness_hj1287_2023` | 烟气黑度 | HJ 1287-2023 |
| `gas_thc_methane_nmhc_hj1332_2023` | 总烃、甲烷、非甲烷总烃 | HJ 1332-2023 |

## 9. 联调注意事项

1. 调用方应以 `card_id` 作为 MethodCard 稳定标识，不要依赖 `factor` 文本做唯一判断。
2. `GET /api/v1/method-cards` 只返回公开摘要，不返回完整详情。
3. 详情展示应调用 `GET /api/v1/method-cards/{card_id}/public`。
4. `COD 怎么测？` 当前必须保持未命中，不能自动匹配高锰酸盐指数。
5. `CODMn 怎么测？` 当前应命中 `water_permanganate_index_hj1445_2026`。
6. 当前阶段不包含 RAG、embedding、pgvector、LLM answering、PDF parsing。
7. `source_documents.file_path` 只作为库内来源路径元数据，不通过公开接口返回。

