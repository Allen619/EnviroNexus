# enviro-nexus-knowledge 启动部署说明

本文档说明 `enviro-nexus-knowledge` 在本地 POC 环境中的启动步骤。当前部署方式为：

```text
PostgreSQL: Docker Compose
Knowledge API: uv + uvicorn
```

## 1. 前置要求

本机需要已安装：

- Docker Desktop
- uv
- Python 3.12，由 `uv` 自动管理即可

进入项目目录：

```powershell
cd enviro-nexus/enviro-nexus-knowledge
```

## 2. 启动 PostgreSQL

```powershell
docker compose up -d postgres
```

数据库连接信息：

| 项目 | 值 |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `15432` |
| Database | `enviro_nexus_knowledge` |
| User | `enviro_nexus` |
| Password | `enviro_nexus_dev` |
| Docker volume | `enviro_nexus_knowledge_pgdata` |

检查容器状态：

```powershell
docker compose ps
```

## 3. 安装依赖

```powershell
uv sync
```

说明：当前默认配置已经匹配 `docker-compose.yml` 中的 PostgreSQL 连接；本地默认不需要额外创建 `.env`。

## 4. 执行数据库迁移

```powershell
uv run alembic upgrade head
```

该步骤会创建或更新：

- `source_documents`
- `method_cards`
- `factor_aliases`
- `knowledge_import_batches`

## 5. 导入 seed 数据

```powershell
uv run python -m app.services.import_service --seed data/seed --mode upsert
```

说明：

- 当前 seed 包含 5 张 MethodCard。
- `upsert` 是幂等导入；重复执行不会重复创建 `source_documents`、`method_cards`、`factor_aliases` 业务数据。
- `knowledge_import_batches` 会为每次导入记录一条审计批次。

## 6. 启动 Knowledge API

开发模式：

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

普通运行模式：

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010
```

服务地址：

```text
http://127.0.0.1:8010
```

接口文档：

| 文档 | 地址 |
| --- | --- |
| Swagger UI | `http://127.0.0.1:8010/docs` |
| ReDoc | `http://127.0.0.1:8010/redoc` |
| OpenAPI JSON | `http://127.0.0.1:8010/openapi.json` |

## 7. 启动验收

### 7.1 健康检查

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/health"
```

预期：

```json
{
  "status": "ok",
  "service": "enviro-nexus-knowledge",
  "api_version": "v1",
  "database": "ok"
}
```

### 7.2 查询 pH

PowerShell 推荐使用 `Invoke-RestMethod`：

```powershell
$body = @{ query = "pH 怎么测？" } | ConvertTo-Json -Compress
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8010/api/v1/factors/query" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

预期：

```text
matched = true
card_id = water_ph_hj1147_2020
answer.evidence_refs 非空
```

### 7.3 验证 COD 不误命中

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

### 7.4 验证 CODMn 命中

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

### 7.5 验证方法卡接口

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards"
```

预期：

```text
count = 5
```

```powershell
curl.exe "http://127.0.0.1:8010/api/v1/method-cards/water_ph_hj1147_2020/public"
```

预期：

```text
card.card_id = water_ph_hj1147_2020
card.evidence_refs 非空
```

## 8. 运行测试

```powershell
uv run pytest -v
```

integration 测试依赖真实 Docker PostgreSQL，运行前必须确保已执行：

```powershell
docker compose up -d postgres
uv run alembic upgrade head
```

## 9. 停止服务

停止 API：

- 如果在当前终端运行 uvicorn，按 `Ctrl+C`。
- 如果需要查找占用 `8010` 的进程：

```powershell
Get-NetTCPConnection -LocalPort 8010 -State Listen | Select-Object -First 1
```

停止指定进程：

```powershell
Stop-Process -Id <PID>
```

停止 PostgreSQL 容器：

```powershell
docker compose down
```

说明：`docker compose down` 不会删除 named volume，数据库数据仍保留在 `enviro_nexus_knowledge_pgdata` 中。

如需删除本地数据库数据，必须明确执行 volume 删除命令；不要在不确认数据用途的情况下删除 volume。

## 10. 常见问题

### 10.1 8010 端口已有旧服务

表现：

```text
新增接口返回 404，或 Swagger UI 中看不到新接口。
```

处理：

```powershell
Get-NetTCPConnection -LocalPort 8010 -State Listen | Select-Object -First 1
Stop-Process -Id <PID>
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010
```

### 10.2 数据库连接失败

检查 PostgreSQL 容器：

```powershell
docker compose ps
docker compose logs postgres
```

重新启动：

```powershell
docker compose up -d postgres
uv run alembic upgrade head
```

