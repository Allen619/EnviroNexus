# enviro-nexus-api 项目框架设计

## 技术栈

- **Web 框架**: FastAPI
- **包管理**: uv
- **HTTP 客户端**: httpx（异步）
- **配置管理**: pydantic-settings
- **容器化**: Docker（可选，本地可不依赖 Docker 启动）

## 项目结构

```
enviro-nexus-api/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── dependencies.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── health.py
│   │       └── factors.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── clients/
│   │   ├── __init__.py
│   │   └── knowledge_client.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── factor_service.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── factor_query.py
│   │   └── common.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   └── middleware/
│       ├── __init__.py
│       └── request_id.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_health.py
    └── test_factors.py
```

## 请求流程

```
前端请求
  → middleware/request_id.py (注入 request_id)
  → api/v1/factors.py (路由层，参数校验)
  → services/factor_service.py (业务编排)
  → clients/knowledge_client.py (调用知识服务)
  → schemas/factor_query.py (响应序列化)
  → 返回统一格式响应
```

## 各层职责

| 模块 | 职责 | 不做什么 |
|---|---|---|
| `api/v1/*.py` | 参数校验、调用 service、返回响应 | 不含业务逻辑 |
| `services/factor_service.py` | 编排业务流程、异常转换、响应组装 | 不直接发 HTTP 请求 |
| `clients/knowledge_client.py` | 封装对知识服务的 HTTP 调用 | 不做业务判断 |
| `dependencies.py` | 提供 httpx.AsyncClient、settings 等依赖 | 不含业务逻辑 |
| `schemas/*.py` | 请求/响应模型定义 | 不含逻辑代码 |
| `core/exceptions.py` | 统一异常类和全局异常处理器 | — |
| `middleware/request_id.py` | 注入/传递 request_id | — |

## 关键代码模式

### 配置管理 (`config/settings.py`)

```python
class Settings(BaseSettings):
    app_name: str = "enviro-nexus-api"
    app_version: str = "0.1.0"
    debug: bool = False
    knowledge_service_base_url: str = "http://127.0.0.1:8010/api/v1"
    knowledge_service_timeout: float = 10.0
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

通过环境变量覆盖，Docker 部署时设 `KNOWLEDGE_SERVICE_BASE_URL` 指向知识服务容器名即可。

### 依赖注入 (`dependencies.py`)

```python
async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient() as client:
        yield client

def get_settings() -> Settings:
    return Settings()
```

路由层通过 `Depends()` 注入，测试时轻松替换为 mock。

### 统一响应格式 (`schemas/common.py`)

```python
class ApiResponse(BaseModel):
    api_version: str = "v1"
    request_id: str | None = None
```

所有业务响应继承此模型，保证 `api_version` 和 `request_id` 一致。

### 统一异常处理 (`core/exceptions.py`)

- `KnowledgeServiceError` — 知识服务调用失败
- 因子未命中 — 业务正常分支，由 Service 返回 `success=true` + `code=FACTOR_NOT_FOUND`（非异常）
- 全局 exception_handler 将异常转为统一 JSON 格式（`build_error_response`）

### 日志 (`core/logging.py`)

结构化日志，每条日志自动携带 `request_id`，方便链路追踪。

## API 接口

### 路由注册 (`api/v1/router.py`)

```python
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(factors.router, tags=["factors"])
```

后续加 `v2` 只需新建 `api/v2/` 目录，`main.py` 中 include 即可。

### 接口列表

| 接口 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 健康检查 | GET | `/api/v1/health` | 返回服务状态 |
| 因子查询 | POST | `/api/v1/factors/query` | 转发到知识服务，返回结构化结果 |
| 方法卡详情 | GET | `/api/v1/method-cards/{card_id}` | 转发到知识服务，返回完整方法卡 |

请求/响应模型严格对齐 POC 第八章的 JSON 结构。

## Docker 设计（可选）

- `Dockerfile`：多阶段构建，基于 `python:3.12-slim`，uv 安装依赖
- `docker-compose.yml`：定义 `api` 和 `knowledge` 两个服务
- 本地不用 Docker 时，直接 `uv run uvicorn app.main:app --port 8080` 启动

### 端口与环境变量

| 服务 | 默认端口 | 关键环境变量 |
|---|---|---|
| enviro-nexus-api | 8080 | `KNOWLEDGE_SERVICE_BASE_URL`, `LOG_LEVEL`, `DEBUG` |
| enviro-nexus-knowledge | 8010 | — |

## 核心依赖

运行时：`fastapi`, `uvicorn`, `httpx`, `pydantic-settings`

开发时：`pytest`, `pytest-asyncio`, `httpx`（测试客户端）
