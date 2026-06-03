# Day 0：enviro-nexus-knowledge 工程和数据库底座执行计划

## 本轮目标

创建 `enviro-nexus-knowledge` 子项目，使其成为可启动的 FastAPI + PostgreSQL + SQLAlchemy + Alembic Python 服务，并实现真实检查数据库连接的 `GET /api/v1/health` 接口。

## 当前检查结果

`enviro-nexus-knowledge` 目录已存在，但目前只有 `.gitkeep`。当前未发现 `pyproject.toml`、`docker-compose.yml`、`alembic.ini`、`app/`、`tests/` 等 Day 0 工程文件。

## 需要创建或修改的文件

- 创建 `README.md`：说明项目定位、本地启动、常用命令和 Day 0 验收命令。
- 创建 `pyproject.toml`：声明 uv 项目和 Day 0 所需依赖。
- 创建 `.env.example`：提供本地开发配置样例。
- 创建 `docker-compose.yml`：使用 Docker Compose 启动 `postgres:16`，端口 `15432:5432`，数据目录使用 named volume。
- 创建 `data/backups/`：作为 PostgreSQL 备份挂载目录。
- 创建 `alembic.ini`、`alembic/env.py`、`alembic/versions/0001_create_day0_tables.py`：提供 Alembic 迁移入口和 Day 0 四张表。
- 创建 `app/settings.py`：从环境变量读取 `APP_ENV`、`API_VERSION`、`DATABASE_URL`、`LOG_LEVEL`。
- 创建 `app/db/session.py`：创建 SQLAlchemy engine 和会话工厂。
- 创建 `app/db/models.py`：定义 `source_documents`、`method_cards`、`factor_aliases`、`knowledge_import_batches` ORM 模型。
- 创建 `app/api/routes/health.py`：实现数据库健康检查接口。
- 创建 `app/main.py`：创建 FastAPI app 并挂载 `/api/v1` 路由。
- 创建 `tests/integration/test_health_api.py`：验证 health API 在数据库可用时返回预期字段。

## 数据库设计

Alembic migration 按固定顺序创建四张表：

1. `source_documents`
2. `method_cards`
3. `factor_aliases`
4. `knowledge_import_batches`

关键约束：

- `source_documents.status` 限定为 `active`、`draft`、`superseded`。
- `method_cards.source_doc_id` 外键引用 `source_documents.doc_id`。
- `method_cards.review_status` 限定为 `draft`、`reviewing`、`approved`、`rejected`。
- `method_cards.answer_visibility` 限定为 `enabled`、`disabled`。
- `factor_aliases.card_id` 外键引用 `method_cards.card_id`。
- `factor_aliases` 使用 `UNIQUE(normalized_alias, card_id)` 防止同卡重复别名。
- `method_cards.card_json` 使用 PostgreSQL `JSONB` 并建立 GIN 索引。

## API 设计

实现 `GET /api/v1/health`。

数据库可用时返回：

```json
{
  "status": "ok",
  "service": "enviro-nexus-knowledge",
  "api_version": "v1",
  "database": "ok"
}
```

数据库不可用时返回 HTTP 503：

```json
{
  "status": "error",
  "service": "enviro-nexus-knowledge",
  "api_version": "v1",
  "database": "unavailable"
}
```

## 测试设计

- 先创建 `tests/integration/test_health_api.py`，测试 `/api/v1/health` 在数据库可用时返回 `status=ok`、`service=enviro-nexus-knowledge`、`api_version=v1`、`database=ok`。
- 测试不使用假的 health 数据，接口必须执行真实数据库连接检查。
- 执行测试前需要先启动 PostgreSQL，并执行 Alembic migration。

## 验收命令

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv sync
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest -v
curl http://localhost:8010/api/v1/health
```

## 不做事项

- 不修改 `enviro-nexus-api`。
- 不修改 `enviro-nexus-web`。
- 不做 Day 1 MethodCard seed 数据。
- 不实现因子查询业务逻辑。
- 不实现 PDF 解析。
- 不引入大模型、向量检索或 pgvector。
- 不做后台管理 UI。
- 不做任务单解析。
