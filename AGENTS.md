# AGENTS.md — 课影 (EduCast)

## 项目概述
课影 (EduCast) 是一个面向高校教学的智能视频生产平台。教师上传课件/讲稿，系统自动完成解析、脚本编排、配音、画面合成与数字人讲解，产出带章节导航与字幕的结构化教学视频。**全程不训练模型，所有生成能力通过可插拔的外部 API 提供。**

### 核心架构
```
表现层: React + TypeScript + Vite + Ant Design
应用层: FastAPI（Python 3.11+）
编排层: 任务流水线 + 课程脚本 IR + Provider 适配层 + WebSocket 实时推送
能力层: LLM/TTS/数字人/视频生成（外部 API）+ FFmpeg/manim（本地）
数据层: SQLite/PostgreSQL + 本地文件系统/MinIO
模板系统: 微课/慕课/实验课三模板（配色+prompt风格+编排偏好）+ 模板市场
```

### 核心数据流
`上传课件 → 文档解析 → IR草稿 → LLM脚本编排 → 教师审核 → 并行生成(TTS+渲染+数字人+生成式片段) → FFmpeg合成 → 资源入库 → 导出`

## 构建与运行命令
- 后端安装依赖: `cd backend && pip install -r requirements.txt`
- 后端运行: `cd backend && uvicorn app.main:app --reload --port 8000`
- 前端安装依赖: `cd frontend && npm install`
- 前端运行: `cd frontend && npm run dev`
- 运行后端测试: `cd backend && pytest tests/ -v`
- 前端类型检查: `cd frontend && npx tsc --noEmit`
- 代码格式化: `cd backend && black backend/ && cd ../frontend && npx prettier --write src/`
- 代码检查: `cd backend && ruff check backend/ && cd ../frontend && npx eslint src/`

## 行为边界
- **始终**: 运行测试后再提交代码
- **始终**: 新增 API 端点必须包含 Type Hints 和 Pydantic Schema
- **始终**: 外部 API 调用必须通过 Provider 适配层
- **始终**: Pydantic Schema 中 UUID 字段使用 UUID 类型（非 str）
- **始终**: SQLAlchemy 异步查询后返回对象前使用 selectinload 预加载关系
- **始终**: 同步阻塞操作（文件解析、图片渲染）必须包裹 `asyncio.to_thread`
- **始终**: 任务状态更新使用 `app.utils.task_helpers.update_task_status`（自带 WebSocket 广播）
- **先问再做**: 修改 IR Schema、数据库 Schema、添加新依赖
- **禁止**: 提交 API 密钥或 `.env` 文件
- **禁止**: 在代码中硬编码 API 密钥
- **禁止**: 直接调用外部 API，必须走 Provider 适配层
- **禁止**: 修改 `.agents/` 目录下的配置文件（除非用户明确要求）

## 代码风格
- **Python**: PEP 8, Black 格式化, 行宽 88, Type Hints, Pydantic v2
- **TypeScript**: strict mode, ESLint + Prettier, 单引号, 2 空格缩进
- **命名**: Python `snake_case` / TypeScript `camelCase` / 组件 `PascalCase`
- **Commit**: Conventional Commits 格式 (`feat(parser): 支持 PPTX 备注提取`)

## 项目性质
**专业实训项目**（单人、演示级），6 个核心模块全部实现。分期策略：
- P1: 跑通骨架（解析→脚本→TTS+课件渲染→合成→入库）
- P2: 接生成能力（数字人 + 生成式片段）
- P3: 加深增强（评估出题、manim、React 控制台）
- P4: 功能增强（多视频模板、知识图谱可视化、随堂测试、视频水印、版本对比）
- P5: 用户系统与设置面板
- P6: 安全加固与功能扩展（批量上传、WebSocket、标注、模板市场、学情分析）

## 外部资源
- 需求分析文档: [课影-需求分析文档.md](./课影-需求分析文档.md)
