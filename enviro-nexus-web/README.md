# enviro-nexus-web

环检智枢 EnviroNexus 前端工作台。

## 技术栈

- **Vite + React 19 + TypeScript** — 构建与开发框架
- **Tailwind CSS v4** — 通过 `@tailwindcss/vite` 插件，CSS-first 配置
- **shadcn/ui** — 基础组件库（radix 底座，new-york 风格，CSS 变量主题）
- **AI SDK**（`ai` / `@ai-sdk/react`）— AI 交互状态与流式处理
- **AI Elements** — 基于 shadcn/ui 的 AI 原生组件（位于 `src/components/ai-elements/`）
- **Streamdown** — 流式 Markdown 渲染（表格 / 代码高亮 / 数学公式 / Mermaid）

## 本地开发

```bash
pnpm install
pnpm dev        # 启动开发服务器，默认 http://localhost:3000
pnpm build      # 类型检查 + 生产构建
pnpm preview    # 预览生产构建
pnpm lint       # 代码检查
```

## 目录结构

```
src/
├── components/
│   ├── ui/            # shadcn/ui 组件（registry 拷贝，已在 lint 中忽略）
│   ├── ai-elements/   # AI Elements 组件（registry 拷贝，已在 lint 中忽略）
│   └── chat-workbench.tsx  # AI 工作台示例（含模拟流式 Markdown 渲染）
├── lib/utils.ts       # cn() 等工具函数
├── App.tsx
├── main.tsx
└── index.css          # Tailwind 入口 + shadcn 主题变量
```

> `@/` 别名指向 `src/`（见 `vite.config.ts` 与 `tsconfig.*.json`）。

## 组件库说明

- 新增 shadcn 组件：`pnpm dlx shadcn@latest add <component>`
- 新增 AI Elements 组件：`pnpm dlx shadcn@latest add https://ai-sdk.dev/elements/api/registry/all.json`
- AI Elements 仅支持 shadcn 的 CSS 变量主题模式（已启用）。
- 接入真实模型时，使用 `@ai-sdk/react` 的 `useChat` 管理消息与流式状态，
  并用 `MessageResponse`（内部基于 Streamdown）渲染助手回复。
