# enviro-nexus-web

环检智枢 EnviroNexus — 前端工作台

## 本仓库职责

- 提供环检因子查询与多轮对话工作台 UI
- 通过 `src/services/api/` 调用业务后端 (enviro-nexus-api)
- 支持会话列表、历史恢复、流式 Markdown 回复与方法卡引用展示
- 本地开发时由 Vite 将 `/api` 代理至后端，避免跨域

## 本地启动方式

### 前置条件

- **Node.js** 20+（推荐 LTS；与 Vite 8 / TypeScript 6 兼容）
- **pnpm** 9+（本项目使用 pnpm 管理依赖）

#### 安装 Node.js

任选一种方式，安装 **20.x 或 22.x LTS** 即可。

**macOS（Homebrew）**

```bash
brew install node@22
# 若命令 node 不可用，按 brew 提示将 node@22 加入 PATH
node -v   # 应 ≥ v20
npm -v
```

**macOS / Linux（nvm，便于切换版本）**

```bash
# 安装 nvm：https://github.com/nvm-sh/nvm#installing-and-updating
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# 重新打开终端后：
nvm install 22
nvm use 22
node -v
```

**Windows**

- 官网安装包：https://nodejs.org/（选 LTS）
- 或使用 winget：

```powershell
winget install OpenJS.NodeJS.LTS
node -v
npm -v
```

安装完成后，在终端确认：

```bash
node -v   # 例如 v22.x.x
npm -v
```

#### 安装 pnpm

Node 自带 `corepack` 时，推荐用其启用 pnpm（若尚未安装）：

```bash
# 使用 npm 全局安装
npm install -g pnpm
```

### 安装依赖

在 `enviro-nexus-web/` 目录下执行：

```bash
pnpm install
```

### 启动项目

```bash
pnpm dev
```

启动后访问：

- 工作台：http://localhost:3000

开发模式下，浏览器请求 `/api/v1/*` 会由 Vite 代理到 `http://localhost:8080`（见 `vite.config.ts`），需先启动业务后端。

### 可选环境变量

可在项目根目录创建 `.env.local`（勿提交密钥）：

| 变量                | 默认值                | 说明                                                                                 |
| ------------------- | --------------------- | ------------------------------------------------------------------------------------ |
| `VITE_API_BASE_URL` | （空，走同源 `/api`） | 生产或直连后端时的 API 根地址，如 `https://api.example.com`（不含 `/api/v1` 路径段） |
| `VITE_USER_ID`      | `user-001`            | POC 用户标识，对应请求头 `X-User-Id`，须与后端会话归属一致                           |

示例：

```bash
# .env.local
VITE_USER_ID=user-001
# VITE_API_BASE_URL=https://your-api-host
```

## 常用命令

| 命令           | 说明                                   |
| -------------- | -------------------------------------- |
| `pnpm install` | 安装依赖                               |
| `pnpm dev`     | 本地开发（默认 http://localhost:3000） |
| `pnpm build`   | TypeScript 检查 + 生产构建             |
| `pnpm preview` | 预览生产构建产物                       |
| `pnpm lint`    | ESLint 检查                            |

## 默认端口

| 服务                         | 端口 |
| ---------------------------- | ---- |
| enviro-nexus-web（Vite）     | 3000 |
| enviro-nexus-api（代理目标） | 8080 |
| enviro-nexus-knowledge       | 8000 |

## 联调说明

完整链路需同时启动知识服务与业务后端，再启动本前端：

1. **知识服务**：`enviro-nexus-knowledge` 运行于 `http://localhost:8000`
2. **业务后端**：在 `enviro-nexus-api/` 中执行 `uv run uvicorn app.main:app --port 8080 --reload`（详见 [enviro-nexus-api/README.md](../enviro-nexus-api/README.md)）
3. **前端**：本目录 `pnpm dev`

健康检查（经代理）：

```bash
curl -s http://localhost:3000/api/v1/health
```

典型使用流程与 API 一致：

1. 打开工作台 → 自动或手动创建会话（`POST /api/v1/sessions`，带 `X-User-Id`）
2. 输入问题 → 流式查询（`POST /api/v1/factors/query/stream`）
3. 侧边栏查看历史会话（`GET /api/v1/sessions`）

后端 API 文档：http://localhost:8080/docs

## 技术栈

- **Vite + React 19 + TypeScript** — 构建与开发框架
- **Tailwind CSS v4** — 通过 `@tailwindcss/vite` 插件，CSS-first 配置
- **shadcn/ui** — 基础组件库（radix 底座，new-york 风格，CSS 变量主题）
- **AI SDK**（`ai` / `@ai-sdk/react`）— AI 交互状态与流式处理
- **AI Elements** — 基于 shadcn/ui 的 AI 原生组件（位于 `src/components/ai-elements/`）
- **Streamdown** — 流式 Markdown 渲染（表格 / 代码高亮 / 数学公式 / Mermaid）

## 项目结构

```
src/
├── components/
│   ├── ui/                 # shadcn/ui 组件
│   ├── ai-elements/        # AI Elements 组件
│   └── chat-workbench.tsx  # 主工作台（会话、流式对话、引用展示）
├── lib/
│   ├── chat-stream.ts      # 流式会话状态与 SSE 解析
│   ├── session-mapper.ts   # API 会话 ↔ 前端模型映射
│   └── session-url.ts      # 会话 URL 同步
├── services/api/           # enviro-nexus-api 客户端
│   ├── client.ts           # 请求基座、X-User-Id、错误处理
│   ├── sessionsController/ # 会话 CRUD
│   ├── factorsController/  # 因子查询与流式查询
│   └── healthController/   # 健康检查
├── App.tsx
├── main.tsx
└── index.css               # Tailwind 入口 + shadcn 主题变量
```

> `@/` 别名指向 `src/`（见 `vite.config.ts` 与 `tsconfig.*.json`）。

## 组件库说明

- 新增 shadcn 组件：`pnpm dlx shadcn@latest add <component>`
- 新增 AI Elements 组件：`pnpm dlx shadcn@latest add https://ai-sdk.dev/elements/api/registry/all.json`
- AI Elements 仅支持 shadcn 的 CSS 变量主题模式（已启用）。
- 助手回复通过 Streamdown 渲染；流式数据来自 `queryFactorStream`（SSE：`meta` → `token` → `done`）。
