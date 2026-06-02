# enviro-nexus-api

环检智枢 EnviroNexus — 业务后端服务

## 本仓库职责

- 接收前端请求（支持多轮会话）
- 调用知识服务 (enviro-nexus-knowledge) 检索方法卡
- 使用 MiniMax-M3（LangChain）生成自然语言回答
- 统一返回格式（含 `reply` 与 `sources` 引用）
- 日志记录、异常处理、健康检查

## 本地启动方式

### 前置条件

- 打开powershell
- 安装uv：
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
- 安装完后根据提示设置环境变量
- uv python install 3.12


### 安装依赖

```bash
uv sync
```

### 启动服务

```bash
uv run uvicorn app.main:app --port 8080 --reload
```

服务启动后访问：
- API 文档：http://localhost:8080/docs
- 健康检查：http://localhost:8080/api/v1/health

## Docker 启动

```bash
docker compose up -d
```

## 常用命令

| 命令 | 说明 |
|---|---|
| `uv sync` | 安装依赖 |
| `uv run uvicorn app.main:app --port 8080 --reload` | 本地开发启动 |
| `uv run pytest` | 运行测试 |
| `uv run pytest -v` | 运行测试（详细输出） |

## 默认端口

| 服务 | 端口 |
|---|---|
| enviro-nexus-api | 8080 |
| enviro-nexus-knowledge | 8000 |

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `KNOWLEDGE_SERVICE_BASE_URL` | `http://localhost:8000` | 知识服务地址 |
| `KNOWLEDGE_SERVICE_TIMEOUT` | `10.0` | 知识服务超时（秒） |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `DEBUG` | `false` | 调试模式 |
| `MINIMAX_API_KEY` | — | MiniMax API Key（生产必填） |
| `MINIMAX_BASE_URL` | `https://api.minimax.chat/v1` | MiniMax OpenAI 兼容地址 |
| `MINIMAX_MODEL` | `MiniMax-M3` | 模型名称 |
| `SESSION_STORE` | `memory` | 会话存储：`memory` 或 `redis` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 地址（`SESSION_STORE=redis` 时） |
| `SESSION_TTL_SECONDS` | `86400` | 会话过期时间（秒） |
| `MAX_RECENT_TURNS` | `6` | 上下文保留最近消息条数 |

### 因子查询（破坏性变更）

`POST /api/v1/factors/query` 请求可增加 `session_id`；响应 `data` 使用 `reply`、`sources`、`session_id`，不再返回结构化 `answer`。详见 `docs/superpowers/specs/2026-06-02-chat-query-minimax-design.md`。

复制 `.env.example` 为 `.env` 并按需修改：

```bash
cp .env.example .env
```

## 联调说明

确保知识服务 (enviro-nexus-knowledge) 已启动并可访问：

```bash
curl http://localhost:8000/api/v1/health
```

## 项目结构

```
app/
├── main.py              # FastAPI 应用入口
├── dependencies.py      # 依赖注入
├── api/v1/              # API 路由（版本化）
├── config/              # 配置管理
├── clients/             # 外部服务客户端
├── services/            # 业务逻辑（含 ChatQueryService、SessionStore）
├── schemas/             # 请求/响应模型
├── llm/                 # MiniMax / LangChain 封装
├── core/                # 异常处理、日志
└── middleware/          # 中间件
```
