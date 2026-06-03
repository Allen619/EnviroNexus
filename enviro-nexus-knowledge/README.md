# enviro-nexus-knowledge

`enviro-nexus-knowledge` 是 EnviroNexus POC 阶段的知识服务，负责环保检测标准方法卡（MethodCard）的结构化存储、导入、匹配和公开查询。

## 当前能力

- 基于 PostgreSQL 存储 `source_documents`、`method_cards`、`factor_aliases` 和导入批次记录。
- 支持 MethodCard seed JSON 的 schema 校验和幂等导入。
- 支持检测因子别名匹配和标准化回答生成。
- 支持公开 MethodCard 列表和详情接口。
- 支持 Swagger UI / ReDoc 自动接口文档。

当前已导入 5 张 MethodCard，覆盖 pH、色度、高锰酸盐指数、烟气黑度、总烃/甲烷/非甲烷总烃等 Day 1.5 POC 数据。

## 不在当前范围

- 不做 PDF 自动解析。
- 不做 RAG、embedding、pgvector。
- 不接入大模型问答。
- 不包含 `enviro-nexus-api` 和 `enviro-nexus-web` 的业务实现。

## 技术栈

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL 16
- Docker Compose
- pytest
- uv

## 目录说明

```text
app/
  api/            FastAPI 路由
  core/           归一化、匹配、回答构建等核心逻辑
  db/             SQLAlchemy 模型、仓储和数据库会话
  schemas/        Pydantic schema
  services/       导入和查询服务
alembic/          数据库迁移
data/seed/        MethodCard、source document、alias seed 数据
docs/plans/       阶段实现计划
docs/reports/     阶段验收和覆盖报告
tests/            单元测试和集成测试
deploy.md         本地启动部署说明
```

## 本地启动

启动步骤见：

[deploy.md](./deploy.md)

常规顺序：

```text
docker compose up -d postgres
uv sync
uv run alembic upgrade head
uv run python -m app.services.import_service --seed data/seed --mode upsert
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010
```

## 接口入口

服务启动后：

| 文档 | 地址 |
| --- | --- |
| Swagger UI | `http://127.0.0.1:8010/docs` |
| ReDoc | `http://127.0.0.1:8010/redoc` |
| OpenAPI JSON | `http://127.0.0.1:8010/openapi.json` |

当前主要接口：

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/health` | 健康检查 |
| `POST` | `/api/v1/factors/query` | 检测因子查询 |
| `GET` | `/api/v1/method-cards` | 公开方法卡列表 |
| `GET` | `/api/v1/method-cards/{card_id}/public` | 公开方法卡详情 |

## 测试

集成测试依赖真实 Docker PostgreSQL，不使用 SQLite，不 mock 数据库。运行前确保 PostgreSQL 已启动，并已执行迁移。

```powershell
uv run pytest -v
```

## 数据边界

当前公开查询只基于已导入的 MethodCard seed 数据。`source_documents.file_path` 仅作为来源路径元数据记录，不会在 Day 1.x 阶段阻塞导入，也不会作为公开接口字段返回。
