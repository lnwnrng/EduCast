# 课影 EduCast

> 面向高校教学的智能视频生产平台

教师上传课件/讲稿，系统自动完成解析、脚本编排、配音、画面合成与数字人讲解，产出带章节导航与字幕的结构化教学视频。**全程不训练模型，所有生成能力通过可插拔的外部 API 提供。**

## 核心架构

```
表现层: React + TypeScript + Vite + Ant Design
应用层: FastAPI（Python 3.11+）
编排层: 任务流水线 + 课程脚本 IR + Provider 适配层
能力层: LLM/TTS/数字人/视频生成（外部 API）+ FFmpeg/manim（本地）
数据层: SQLite(毕设)/PostgreSQL + 本地文件系统/MinIO
```

## 核心数据流

```
上传课件 → 文档解析 → IR草稿 → LLM脚本编排 → 教师审核
→ 并行生成(TTS+渲染+数字人+生成式片段) → FFmpeg合成 → 资源入库 → 导出
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- FFmpeg（已加入系统 PATH）

### 后端

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env  # 编辑 .env 填入 API Key

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

### 前端

```bash
cd frontend
npm install

# 启动开发服务器
npm run dev
```

前端地址：http://localhost:5173

## 项目结构

```
EduCast/
├── backend/               # 后端 (FastAPI)
│   ├── app/
│   │   ├── main.py        # 入口
│   │   ├── config.py      # 配置
│   │   ├── models/        # 数据库模型
│   │   ├── schemas/       # Pydantic Schema
│   │   ├── api/v1/        # API 路由
│   │   ├── services/      # 业务逻辑
│   │   ├── providers/     # Provider 适配层
│   │   ├── pipeline/      # 任务流水线
│   │   ├── ir/            # 课程脚本 IR
│   │   ├── storage/       # 存储抽象
│   │   └── utils/         # 工具函数
│   ├── tests/             # 测试
│   └── alembic/           # 数据库迁移
├── frontend/              # 前端 (React + Vite)
│   └── src/
│       ├── api/           # API 调用层
│       ├── components/    # 通用组件
│       ├── pages/         # 页面组件
│       ├── stores/        # 状态管理
│       ├── types/         # TypeScript 类型
│       └── styles/        # 全局样式
└── .env.example           # 环境变量模板
```

## 开发命令

| 命令 | 说明 |
|------|------|
| `uvicorn app.main:app --reload --port 8000` | 启动后端 |
| `cd frontend && npm run dev` | 启动前端 |
| `pytest tests/ -v` | 运行后端测试 |
| `cd frontend && npm test` | 运行前端测试 |
| `black backend/` | Python 代码格式化 |
| `ruff check backend/` | Python 代码检查 |

## 实施分期

| 阶段 | 目标 | 说明 |
|------|------|------|
| **P1** | 跑通骨架 | PPTX→脚本→TTS+课件渲染→合成 MP4→入库 |
| **P2** | 接生成能力 | 数字人 + 生成式片段 |
| **P3** | 加深增强 | 评估出题、manim、React 控制台 |

## License

MIT
