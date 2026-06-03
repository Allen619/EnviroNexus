# enviro-nexus-knowledge

`enviro-nexus-knowledge` 是 EnviroNexus POC 阶段的环保检测标准方法知识服务。

当前已完成 Day 0 工程底座，并在 Day 1 用 `water_ph_hj1147_2020` 单张 MethodCard 打通 pH 查询纵向闭环。

## 本地启动

PostgreSQL 使用 Docker Compose 创建，不需要在 Windows 宿主机安装 PostgreSQL。数据库镜像为 `postgres:16`，容器端口 `5432` 映射到本地 `15432`，数据目录使用 Docker named volume `enviro_nexus_knowledge_pgdata`。

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv sync
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

## 常用命令

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose down
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv sync
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run python -m app.services.import_service --seed data/seed --mode upsert
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest -v
curl http://localhost:8010/api/v1/health
```

## Day 1 pH MethodCard 闭环

Day 1 只做 pH，不读取、不解析 PDF，不引入大模型，不引入向量检索，不继续 Day 2。`source_documents.file_path` 只作为来源路径元数据记录，导入服务不会因为本地 PDF 文件不存在而失败。

纵向链路：

```text
seed JSON
-> MethodCard Schema 校验
-> import service 幂等导入 PostgreSQL
-> factor_aliases 规则匹配
-> answer_builder / evidence_builder
-> POST /api/v1/factors/query
```

导入 seed：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run python -m app.services.import_service --seed data/seed --mode upsert
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run python -m app.services.import_service --seed data/seed --mode upsert
```

连续导入两次后，`source_documents`、`method_cards`、`factor_aliases` 不产生重复业务数据；`knowledge_import_batches` 每次导入新增一条成功审计记录。

查询接口：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"pH 怎么测？\"}"
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"水样酸碱度用什么标准？\"}"
curl -X POST http://localhost:8010/api/v1/factors/query -H "Content-Type: application/json" -d "{\"query\":\"COD 怎么测？\"}"
```

pH 和酸碱度会命中 `water_ph_hj1147_2020`，并返回非空 `answer.evidence_refs`。`COD 怎么测？` 返回 `matched=false`，不会误命中 pH。

## Day 0 验收命令

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv sync
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest -v
curl http://localhost:8010/api/v1/health
```

## 测试说明

integration 测试会真实请求 Docker PostgreSQL，不使用 SQLite，不 mock 数据库。运行测试前需要先启动 PostgreSQL，并执行 Alembic migration：

```bash
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && docker compose up -d postgres
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run alembic upgrade head
cd /d/szy/code/my-project/enviro-nexus/enviro-nexus-knowledge && uv run pytest -v
```
