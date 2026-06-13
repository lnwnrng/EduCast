# 课影 EduCast — 前端

基于 React 18 + TypeScript + Vite + Ant Design 构建的教学视频生产平台前端。

## 技术栈

| 技术 | 用途 |
|------|------|
| React 18 | UI 框架 |
| TypeScript | 类型安全 |
| Vite | 构建工具 & 开发服务器 |
| Ant Design | UI 组件库 |
| Zustand | 状态管理 |
| React Router | 路由 |
| Axios | HTTP 请求 |
| ECharts | 知识图谱可视化 |

## 开发命令

| 命令 | 说明 |
|------|------|
| `npm install` | 安装依赖 |
| `npm run dev` | 启动开发服务器（热重载） |
| `npm run build` | 生产构建 |
| `npm run lint` | ESLint 代码检查 |
| `npx tsc -b` | TypeScript 类型检查 |

## 目录结构

```
src/
├── api/                # Axios API 调用层
├── components/         # 通用 UI 组件
│   └── common/         # PageHeader 等通用组件
├── pages/              # 页面组件
│   ├── Login/          # 登录
│   ├── Register/       # 注册（邮箱验证码）
│   ├── Dashboard/      # 仪表盘
│   ├── Projects/       # 项目列表
│   ├── Upload/         # 上传 & 解析
│   ├── ScriptEditor/   # 脚本编辑器
│   ├── Workspace/      # 工作空间
│   ├── Preview/        # 视频预览
│   ├── Resources/      # 资源管理
│   ├── KnowledgeGraph/  # 知识图谱可视化
│   ├── Assessment/     # 随堂测试
│   ├── Monitoring/     # 系统监控
│   ├── Settings/       # 系统设置
│   └── Admin/          # 管理后台
├── stores/             # Zustand 状态管理
├── types/              # TypeScript 类型定义
└── styles/             # 全局样式
```

## 环境要求

- Node.js 18+
- 后端服务运行在 `http://localhost:8000`（Vite 代理已配置）
