# 因子名透传 Knowledge 服务设计说明

**状态**：已确认，待实施计划  
**日期**：2026-06-04  
**仓库**：enviro-nexus-api  
**关联服务**：enviro-nexus-knowledge  
**关联接口**：`POST /api/v1/factors/query/stream`，`POST /api/v1/factors/query`

## 1. 目标

在现有因子查询流式输出链路中新增前端输入参数 `factor_name`，并将该参数透传给 knowledge 服务的 `POST /api/v1/factors/query` 接口。

现有流式输出仍保持 SSE 协议和事件结构：

1. `meta`：knowledge 检索完成后返回匹配元数据和 sources。
2. `token`：LLM 回复文本片段。
3. `done`：完整回复和 session_id。
4. `error`：流中 LLM 失败。

本次改动不改变 SSE 事件结构，不改变会话归属规则，不改变历史消息的保存格式。

## 2. 当前上下文

knowledge 服务 README 确认当前公开查询入口为：

```text
POST /api/v1/factors/query
```

API 项目当前链路为：

```text
Frontend
  -> POST /api/v1/factors/query/stream
  -> FactorQueryRequest(query, session_id)
  -> ChatQueryService.query_stream(query, session_id, user_id)
  -> ChatQueryService._prepare_turn(...)
  -> KnowledgeClient.query_factor(query)
  -> POST { "query": query } to knowledge /api/v1/factors/query
```

`/api/v1/factors/query` 与 `/api/v1/factors/query/stream` 目前共用 `FactorQueryRequest`，因此推荐同步扩展两个入口，避免同一业务查询出现两套请求体。

## 3. 已确认决策

| 项 | 决策 |
| --- | --- |
| 前端字段名 | `factor_name` |
| 字段类型 | string |
| 必填性 | 必填 |
| 校验 | strip 后非空 |
| 透传目标 | knowledge `POST /api/v1/factors/query` |
| 透传请求体 | `{ "query": query, "factor_name": factor_name }` |
| 同步查询入口 | 一并支持 `factor_name` |
| SSE 事件结构 | 不变 |
| 会话消息内容 | 仍保存用户原始 `query`，不把 `factor_name` 拼入消息 |

## 4. 请求契约

请求头保持不变：

```text
X-User-Id: <user id>
Content-Type: application/json
```

请求体调整为：

```json
{
  "session_id": "uuid",
  "query": "COD 怎么测？",
  "factor_name": "化学需氧量"
}
```

校验规则：

1. `session_id` 必填，非空字符串。
2. `query` 必填，strip 后非空，长度规则沿用现有实现。
3. `factor_name` 必填，strip 后非空字符串。
4. 缺失或空白 `factor_name` 返回现有 JSON 422 `VALIDATION_ERROR`，不打开 SSE 流。

## 5. 数据流

新增参数按以下路径传递：

```text
FactorQueryRequest.factor_name
  -> factors.py route
  -> ChatQueryService.query(...) / query_stream(...)
  -> ChatQueryService._prepare_turn(...)
  -> KnowledgeClient.query_factor(query, factor_name)
  -> POST /api/v1/factors/query
     body: { "query": query, "factor_name": factor_name }
```

`query` 的职责不变：作为用户问题进入会话历史、上下文压缩和 LLM prompt。

`factor_name` 的职责是给 knowledge 服务提供前端指定的检测因子名。API 项目只负责接收、校验和透传；knowledge 服务返回的 `factor`、`matched_alias`、`card_id`、`answer.evidence_refs` 仍作为检索权威结果。

如果当前 knowledge 服务版本尚未显式使用 `factor_name`，API 侧仍会按契约发送该字段；实际匹配行为由 knowledge 服务版本决定。

## 6. 模块变更

| 模块 | 变更 |
| --- | --- |
| `app/schemas/chat_query.py` | `FactorQueryRequest` 增加 `factor_name` 字段和空白校验 |
| `app/api/v1/factors.py` | `query_factor` 与 `query_factor_stream` 将 `body.factor_name` 传入 service |
| `app/services/chat_query_service.py` | `query`、`query_stream`、`_prepare_turn` 接收并传递 `factor_name` |
| `app/clients/knowledge_client.py` | `query_factor` 接收 `factor_name`，请求 knowledge 时包含该字段 |
| `README.md` | 更新同步和流式查询请求示例 |
| `docs/superpowers/specs/2026-06-03-stream-query-design.md` | 可选补充字段契约，避免旧文档误导 |

## 7. 错误处理

| 场景 | 响应形式 | HTTP | code |
| --- | --- | --- | --- |
| 缺失 `factor_name` | JSON | 422 | `VALIDATION_ERROR` |
| 空白 `factor_name` | JSON | 422 | `VALIDATION_ERROR` |
| session 不存在或越权 | JSON | 404 | `SESSION_NOT_FOUND` |
| knowledge 服务失败 | JSON | 502 | `KNOWLEDGE_SERVICE_ERROR` |
| LLM 流中失败 | SSE `error` | 200 | `LLM_SERVICE_ERROR` |

流式接口的流前错误仍由 FastAPI/Pydantic 和现有异常处理器返回 JSON，不能先发送任何 SSE 事件。

## 8. 测试范围

新增或调整测试：

1. `FactorQueryRequest` 接受并 strip `factor_name`。
2. 缺失 `factor_name` 的同步和流式请求返回 422。
3. 空白 `factor_name` 的同步和流式请求返回 422。
4. `ChatQueryService.query()` 调用 `knowledge.query_factor(query, factor_name)`。
5. `ChatQueryService.query_stream()` 调用 `knowledge.query_factor(query, factor_name)`。
6. `KnowledgeClient.query_factor()` 向 knowledge 发送 `{ "query": ..., "factor_name": ... }`。
7. 既有 SSE 顺序 `meta -> token -> done` 和 `error` 行为保持不变。

## 9. 非目标

本次不实现以下内容：

1. 修改 knowledge 服务内部匹配逻辑。
2. 改变 SSE 事件 payload。
3. 把 `factor_name` 写入 session message 内容或 assistant sources。
4. 新增流式 knowledge 检索。
5. 改变 MiniMax / LLM prompt 结构，除非后续实现中发现必须显式展示因子名。
