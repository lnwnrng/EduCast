---
name: react-frontend
description: 当开发 EduCast 前端代码（React/TypeScript/Vite/Ant Design）时使用此技能，定义了组件规范、状态管理和 UI 设计约定。
---

# React 前端开发规范 — 课影 (EduCast)

## 技术栈
- **框架**: React 18+ (函数式组件 + Hooks)
- **语言**: TypeScript（strict mode）
- **构建工具**: Vite 5+
- **UI 组件库**: Ant Design 5+（中文后台）
- **状态管理**: Zustand（轻量）或 React Query（服务端状态）
- **路由**: React Router v6
- **视频预览**: video.js / Plyr（章节/字幕/书签）
- **HTTP 客户端**: Axios
- **国际化**: 中文优先，预留 i18n 接口

## 代码风格
- 使用 **ESLint** + **Prettier** 统一格式
- 字符串使用单引号
- 缩进 2 空格
- 命名规范：
  - 组件: `PascalCase`（如 `ScriptEditor.tsx`）
  - Hooks: `camelCase`，以 `use` 开头（如 `useTaskStatus`）
  - 工具函数: `camelCase`
  - 常量: `UPPER_SNAKE_CASE`
  - 类型/接口: `PascalCase`，接口以 `I` 开头可选
  - CSS 模块: `*.module.css`

## 项目结构约定
```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/                  # API 调用层
│   │   ├── client.ts         # Axios 实例
│   │   ├── projects.ts
│   │   ├── tasks.ts
│   │   └── resources.ts
│   ├── components/           # 通用组件
│   │   ├── Layout/
│   │   ├── VideoPlayer/
│   │   └── common/
│   ├── pages/                # 页面组件
│   │   ├── Upload/           # 上传课件
│   │   ├── ScriptEditor/     # 脚本/分镜编辑
│   │   ├── Preview/          # 成片预览
│   │   ├── Resources/        # 资源管理
│   │   └── Dashboard/        # 监控面板
│   ├── hooks/                # 自定义 Hooks
│   ├── stores/               # 状态管理
│   ├── types/                # TypeScript 类型定义
│   ├── utils/                # 工具函数
│   ├── styles/               # 全局样式与主题
│   └── constants/            # 常量
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## 组件设计原则
1. **函数式组件优先** — 全部使用函数组件 + Hooks，不使用 class 组件
2. **单一职责** — 每个组件只做一件事，超过 200 行考虑拆分
3. **Props 类型化** — 所有 Props 使用 TypeScript 接口定义
4. **Ant Design 优先** — UI 组件优先使用 Ant Design，避免重复造轮子
5. **响应式设计** — 使用 Ant Design Grid 系统，适配桌面/平板
6. **错误边界** — 关键页面包裹 ErrorBoundary
7. **禁止使用 Emoji** — 所有图标/标识一律使用 Ant Design `@ant-design/icons` 组件库中的图标，不得在代码中使用 Emoji 字符

## 状态管理策略
- **服务端状态**: React Query（缓存、自动刷新、乐观更新）
- **客户端状态**: Zustand（轻量 store）
- **表单状态**: Ant Design Form 组件自带管理
- **URL 状态**: React Router searchParams

## API 调用约定
- 统一使用 Axios 实例，配置 baseURL、拦截器
- 请求/响应类型严格定义
- 错误统一在拦截器中处理（Toast 提示）
- 长任务使用轮询或 WebSocket 获取进度

## 关键页面
1. **上传页**: 拖拽上传课件 → 解析进度 → 结果校对
2. **脚本编辑器**: 分镜列表 → 逐个编辑讲稿/画面类型/提示词
3. **生成配置**: 选模板/数字人/TTS 音色/参数 → 成本预估 → 提交
4. **进度追踪**: 实时任务状态（解析中/编排中/生成中/合成中）
5. **成片预览**: 视频播放器 + 章节导航 + 字幕
6. **资源管理**: 列表/检索/预览/下载/版本对比

## 测试
- 组件测试: Vitest + React Testing Library
- E2E 测试: Playwright（可选）
