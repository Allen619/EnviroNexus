# 环检智枢 EnviroNexus

环保检测知识驱动型智能协作平台。

## 子项目

- `enviro-nexus-web/` — 前端工作台
- `enviro-nexus-api/` — 业务后端服务
- `enviro-nexus-knowledge/` — 知识服务

## 本地启动

推荐启动顺序：`enviro-nexus-knowledge` -> `enviro-nexus-api` -> `enviro-nexus-web`。

### 1. 启动知识服务

```powershell
cd enviro-nexus-knowledge
docker compose up -d postgres
uv sync
uv run alembic upgrade head
uv run python -m app.services.import_service --seed data/seed --mode upsert
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

访问：

- API 文档：http://127.0.0.1:8010/docs
- 健康检查：http://127.0.0.1:8010/api/v1/health

### 2. 启动业务后端

```powershell
cd enviro-nexus-api
uv sync
$env:KNOWLEDGE_SERVICE_BASE_URL = "http://127.0.0.1:8010"
uv run uvicorn app.main:app --port 8080 --reload
```

访问：

- API 文档：http://127.0.0.1:8080/docs
- 健康检查：http://127.0.0.1:8080/api/v1/health

### 3. 启动前端工作台

```powershell
cd enviro-nexus-web
pnpm install
pnpm dev
```

访问：

- 前端工作台：http://127.0.0.1:3000

## 更多文档

- `enviro-nexus-knowledge/deploy.md`
- `enviro-nexus-api/README.md`
- `enviro-nexus-web/README.md`
