# 课影 EduCast

> 面向高校教学的智能视频生产平台

教师上传课件/讲稿，系统自动完成解析、脚本编排、配音、画面合成与数字人讲解，产出带章节导航与字幕的结构化教学视频。**全程不训练模型，所有生成能力通过可插拔的外部 API 提供。**

## 功能特性

| 模块 | 功能 |
|------|------|
| **文档解析** | 支持 PPTX / PDF / DOCX 上传，自动提取文本、备注、公式，生成课程脚本 IR |
| **多视频模板** | 微课 / 慕课 / 实验课三种模板，不同配色、LLM 编排风格和分镜偏好 |
| **LLM 脚本编排** | 智谱 GLM 自动润色旁白、拆分分镜、标注公式与生成式片段 |
| **脚本编辑器** | 在线可视化编辑分镜脚本，实时预览旁白与画面 |
| **知识图谱** | ECharts 力导向图可视化课程知识点关系，按章节着色 |
| **随堂测试** | 基于 IR 自动生成练习题，支持选择/填空/简答/计算，在线评分 |
| **TTS 配音** | Edge TTS 生成中文语音，支持多种音色 |
| **课件渲染** | PPT 幻灯片自动光栅化，公式动画（manim / matplotlib 降级） |
| **数字人讲解** | 可插拔数字人 API，本地兜底画中画姓名条 |
| **生成式片段** | CogVideoX 视频生成，为抽象概念补充可视化画面 |
| **视频水印** | FFmpeg drawtext 滤镜，成片右下角半透明文字水印 |
| **版本对比** | 对比不同版本 IR 差异（知识点新增/删除/修改） |
| **FFmpeg 合成** | 并行生成后自动合成 MP4，含字幕、章节导航、水印 |
| **用户系统** | 注册（邮箱验证码）、登录、JWT Token 轮换、角色权限 |
| **管理后台** | 用户管理、审计日志、分类/标签管理、系统监控面板 |
| **资源管理** | 视频资源入库、分类、标签、搜索、导出 |

## 核心架构

```
表现层: React + TypeScript + Vite + Ant Design
应用层: FastAPI（Python 3.11+）
编排层: 任务流水线 + 课程脚本 IR + Provider 适配层
能力层: LLM/TTS/数字人/视频生成（外部 API）+ FFmpeg/manim（本地）
数据层: SQLite(毕设)/PostgreSQL + 本地文件系统
```

### 核心数据流

```
上传课件 → 文档解析 → IR 草稿 → LLM 脚本编排 → 教师审核
→ 并行生成(TTS + 渲染 + 数字人 + 生成式片段) → FFmpeg 合成 → 资源入库 → 导出
```

## 快速开始

### 方式一：一键启动（Windows）

```bash
start.bat
```

自动检测环境、安装依赖、创建数据库、启动前后端服务。

### 方式二：手动启动

#### 环境要求

- Python 3.11+
- Node.js 18+
- FFmpeg（需加入系统 PATH）

#### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 API Key（至少配置 ZHIPU_API_KEY 以启用 LLM）
```

#### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端地址：http://localhost:8000  
API 文档：http://localhost:8000/docs

#### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端地址：http://localhost:5173

### 默认管理员

首次启动自动创建管理员账号：

- 用户名：`admin`
- 密码：`admin123456`

## 项目结构

```
EduCast/
├── backend/                    # 后端 (FastAPI)
│   ├── app/
│   │   ├── main.py             # 应用入口 & 数据库迁移
│   │   ├── config.py           # Pydantic Settings 配置
│   │   ├── database.py         # SQLAlchemy 异步引擎
│   │   ├── exceptions.py       # 自定义异常 & 全局处理器
│   │   ├── models/             # 数据库模型 (User, Project, Task, ...)
│   │   ├── schemas/            # Pydantic 请求/响应 Schema
│   │   ├── api/v1/             # API 路由
│   │   │   ├── auth.py         # 注册、登录、验证码
│   │   │   ├── projects.py     # 项目 CRUD
│   │   │   ├── upload.py       # 文件上传 & 解析
│   │   │   ├── scripts.py      # 脚本编辑 & LLM 编排
│   │   │   ├── tasks.py        # 任务流水线
│   │   │   ├── resources.py    # 资源管理
│   │   │   ├── settings.py     # 运行时配置（API Key 管理）
│   │   │   ├── monitoring.py   # 系统监控
│   │   │   └── admin/          # 管理后台接口
│   │   ├── services/           # 业务逻辑层
│   │   │   ├── settings_service.py  # 运行时配置持久化（JSON 文件）
│   │   ├── providers/          # Provider 适配层
│   │   │   ├── llm/            # 智谱 GLM
│   │   │   ├── tts/            # Edge TTS
│   │   │   ├── digital_human/  # 数字人
│   │   │   ├── video_gen/      # CogVideoX
│   │   │   └── router.py       # Provider 路由 & 降级策略
│   │   ├── pipeline/           # 视频生成流水线
│   │   │   ├── parser.py       # 文档解析
│   │   │   ├── scriptwriter.py # LLM 脚本编排
│   │   │   ├── templates.py    # 视频模板注册表
│   │   │   ├── composer.py     # 合成编排
│   │   │   ├── renderer.py     # 课件渲染
│   │   │   ├── formula.py      # 公式动画（manim / matplotlib 降级）
│   │   │   ├── subtitles.py    # 字幕生成
│   │   │   └── slide_raster.py # 幻灯片光栅化
│   │   ├── ir/                 # 课程脚本 IR 定义 & 校验
│   │   ├── middleware/         # 认证中间件
│   │   └── utils/              # 工具函数 (FFmpeg, JSON, Hash)
│   ├── tests/                  # 后端测试
│   ├── alembic/                # 数据库迁移
│   ├── storage/                # 运行时文件存储
│   └── requirements.txt        # Python 依赖
├── frontend/                   # 前端 (React + Vite)
│   └── src/
│       ├── api/                # Axios API 调用层
│       ├── components/         # 通用 UI 组件
│       ├── pages/              # 页面组件
│       │   ├── Login/          # 登录
│       │   ├── Register/       # 注册（邮箱验证码）
│       │   ├── Dashboard/      # 仪表盘
│       │   ├── Projects/       # 项目列表
│       │   ├── Upload/         # 上传 & 解析
│       │   ├── ScriptEditor/   # 脚本编辑器
│       │   ├── Workspace/      # 工作空间
│       │   ├── Preview/        # 视频预览
│       │   ├── Resources/      # 资源管理
│       │   ├── KnowledgeGraph/  # 知识图谱可视化
│       │   ├── Assessment/     # 随堂测试
│       │   ├── Monitoring/     # 系统监控
│       │   ├── Settings/       # 系统设置（API Key 配置）
│       │   └── Admin/          # 管理后台
│       ├── stores/             # Zustand 状态管理
│       ├── types/              # TypeScript 类型定义
│       └── styles/             # 全局样式
├── .env.example                # 环境变量模板
├── start.bat                   # Windows 一键启动脚本
└── AGENTS.md                   # AI 开发助手指引
```

## 环境变量说明

| 分类 | 变量 | 说明 | 默认值 |
|------|------|------|--------|
| **数据库** | `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./educast.db` |
| **LLM** | `ZHIPU_API_KEY` | 智谱 API 密钥 | — |
| **LLM** | `ZHIPU_MODEL` | 模型名称 | `glm-4.7-flash` |
| **视频生成** | `COGVIDEO_API_KEY` | CogVideoX 密钥 | 回退用 ZHIPU_API_KEY |
| **TTS** | `EDGE_TTS_VOICE` | Edge TTS 音色 | `zh-CN-XiaoxiaoNeural` |
| **邮件** | `RESEND_API_KEY` | Resend 邮件 API 密钥 | — |
| **邮件** | `EMAIL_FROM` | 发件人地址 | — |
| **视频** | `VIDEO_WIDTH` / `VIDEO_HEIGHT` | 输出分辨率 | 1920×1080 |
| **水印** | `WATERMARK_TEXT` | 水印文本 | 课程标题 |
| **水印** | `WATERMARK_IMAGE_PATH` | 图片水印路径 | — |
| **认证** | `JWT_SECRET_KEY` | JWT 签名密钥 | `change-me-...` |
| **认证** | `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期（分钟） | `15` |
| **认证** | `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 有效期（天） | `7` |
| **流水线** | `SKIP_REVIEW` | 跳过人工审核 | `false` |
| **流水线** | `AI_FULL_GEN_DEFAULT` | AI 全自动生成模式 | `false` |
| **成本** | `MAX_COST_PER_TASK` | 单任务最大成本（元） | `10.0` |

完整配置见 [`.env.example`](.env.example)。

## 开发命令

| 命令 | 说明 |
|------|------|
| `uvicorn app.main:app --reload --port 8000` | 启动后端（热重载） |
| `cd frontend && npm run dev` | 启动前端（热重载） |
| `pytest tests/ -v` | 运行后端测试 |
| `cd frontend && npm test` | 运行前端测试 |
| `black backend/` | Python 代码格式化 |
| `ruff check backend/` | Python 代码检查 |
| `cd frontend && npx eslint src/` | TypeScript 代码检查 |
| `cd frontend && npx prettier --write src/` | TypeScript 代码格式化 |

## Provider 适配层

所有外部 API 通过统一的 Provider 接口调用，支持自动降级：

```
LLM:       智谱 GLM-4.7-Flash → DeepSeek → 降级提示
TTS:       Edge TTS（免费）
数字人:     外部 API → 本地画中画兜底
视频生成:   CogVideoX → Placeholder
公式动画:   manim → matplotlib 图片降级
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18, TypeScript, Vite, Ant Design, ECharts, Zustand, Axios |
| 后端 | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 认证 | JWT (python-jose), bcrypt, HttpOnly Cookie |
| 文档解析 | python-pptx, PyMuPDF, pdfplumber, mammoth |
| 视频合成 | FFmpeg, matplotlib, Pillow |
| TTS | Edge TTS |
| LLM | 智谱 GLM-4.7-Flash |
| 视频生成 | 智谱 CogVideoX |

## 实施分期

| 阶段 | 目标 | 状态 |
|------|------|------|
| **P1** | 跑通骨架：PPTX → 脚本 → TTS + 课件渲染 → 合成 MP4 → 入库 | ✅ |
| **P2** | 接生成能力：数字人 + 生成式片段 | ✅ |
| **P3** | 加深增强：评估出题、manim、管理后台 | ✅ |
| **P4** | 功能增强：多模板、知识图谱、随堂测试、水印、版本对比 | ✅ |
| **P5** | 用户系统、设置面板、管理后台增强、全面安全审计 | ✅ |

## License

MIT
