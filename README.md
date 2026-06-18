# 课影 EduCast

> 面向高校教学的智能视频生产平台

教师上传课件/讲稿，系统自动完成解析、脚本编排、配音、画面合成与数字人讲解，产出带章节导航与字幕的结构化教学视频。**全程不训练模型，所有生成能力通过可插拔的外部 API 提供。**

## 功能特性

| 模块 | 功能 |
|------|------|
| **文档解析** | 支持 PPTX / PDF / DOCX / MD / TXT 上传，自动提取文本、备注、公式，生成课程脚本 IR |
| **批量上传** | 多文件同时上传或 ZIP 压缩包自动解压，每个文件创建独立项目 |
| **多视频模板** | 微课 / 慕课 / 实验课三种模板 + 模板市场自定义模板 |
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
| **视频片段重生成** | 不满意某个分镜时，只重新生成该片段而非整段视频 |
| **视频标注** | 时间线批注、知识点标记、颜色分类，方便学生跳转复习 |
| **学情分析** | 任务历史、成本统计、资源汇总、标注统计看板 |
| **FFmpeg 合成** | 并行生成后自动合成 MP4，含字幕、章节导航、水印 |
| **实时进度推送** | WebSocket 实时推送任务进度，替代轮询机制 |
| **用户系统** | 注册（邮箱验证码）、登录、JWT Token 轮换、角色权限 |
| **安全加固** | JWT 启动校验、Logout 黑名单、全局限速、文件内容嗅探、全局 500 处理器 |
| **管理后台** | 用户管理、审计日志、分类/标签管理、系统监控面板 |
| **资源管理** | 视频资源入库、分类、标签、搜索、导出 |
| **模板市场** | 浏览/创建/分享视频模板，自定义配色、字体、片头片尾 |

## 核心架构

```
表现层: React + TypeScript + Vite + Ant Design
应用层: FastAPI（Python 3.11+）
编排层: 任务流水线 + 课程脚本 IR + Provider 适配层 + WebSocket 实时推送
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

> **注意**：首次启动前，请先完成下方 [环境配置](#环境配置) 步骤（复制 `.env` 并填写必要的 API Key）。

### 方式二：手动启动

#### 环境要求

- Python 3.11+
- Node.js 18+
- FFmpeg（需加入系统 PATH）

---

## 环境配置

### 配置文件层级

| 文件 | 作用 | 是否提交 Git |
|------|------|:---:|
| `backend/.env` | 实际生效的环境变量（含密钥） | ❌ 已 gitignore |
| `.env.example` | 环境变量模板（无真实密钥） | ✅ |
| `backend/storage/_runtime_settings.json` | **Web 界面**动态保存的 API Key（优先于 .env） | ❌ |

> **优先级**：Web 界面运行时设置 > `.env` 环境变量 > `config.py` 默认值

### 第一步：创建 .env 文件

```bash
copy .env.example backend\.env
```

> `.env` 必须放在 `backend/` 目录下，与 `config.py` 同目录。`uvicorn` 启动时自动加载。

### 第二步：配置环境变量

#### 快速配置摘要

| 必要性 | 变量 | 说明 |
|--------|------|------|
| 🔴 必填 | `JWT_SECRET_KEY` | 用 `python -c "import secrets; print(secrets.token_hex(32))"` 生成 64 位随机密钥 |
| 🔴 必填 | `ZHIPU_API_KEY` | 在 [open.bigmodel.cn](https://open.bigmodel.cn) 注册获取（GLM-4.7-Flash 免费） |
| 🟡 推荐 | `RESEND_API_KEY` | 如需注册功能，在 [resend.com](https://resend.com) 获取 |
| 🟡 推荐 | `EMAIL_FROM` | 需与 Resend 验证域名一致，如 `EduCast <noreply@yourdomain.com>` |
| 🟢 可选 | 其余全部 | 默认值已内置于 `config.py`，可直接使用，需要时再改 |

#### 完整 .env 模板

以下为 `backend/.env` 的完整内容，**复制后只需修改标注行**：

```ini
# ========================================
# 课影 EduCast — 环境变量配置
# 复制为 backend/.env 并填入真实值
# ========================================

# ---------- 数据库 ----------
DATABASE_URL=sqlite+aiosqlite:///./educast.db

# ---------- 存储 ----------
STORAGE_ROOT=./storage

# ---------- CORS ----------
CORS_ORIGINS=["http://localhost:5173"]

# ---------- Provider API Keys ----------
# 智谱 GLM-4.7-Flash（免费，2026-01 起替代 GLM-4.5-Flash）
ZHIPU_API_KEY=你的智谱API密钥            ← 🔴 必填
# CogVideoX（视频生成，留空自动回退用 ZHIPU_API_KEY）
COGVIDEO_API_KEY=
# 数字人 API（留空则本地画中画兜底）
DIGITAL_HUMAN_API_KEY=

# ---------- LLM（智谱 GLM）----------
ZHIPU_MODEL=glm-4.7-flash
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_TIMEOUT=60.0

# ---------- 生成式片段（智谱 CogVideoX，模块五）----------
COGVIDEO_BASE_URL=https://open.bigmodel.cn/api/paas/v4
COGVIDEO_MODEL=cogvideox-flash
VIDEO_GEN_TIMEOUT=300.0
VIDEO_GEN_POLL_INTERVAL=5.0

# ---------- 数字人（模块四）----------
DIGITAL_HUMAN_AVATAR_NAME=AI 讲师

# ---------- 公式动画 ----------
FORMULA_ENGINE=auto

# ---------- TTS ----------
EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural

# ---------- 路由与成本控制 ----------
DEFAULT_ROUTING_STRATEGY=free_first
MAX_COST_PER_TASK=10.0
MAX_COST_PER_PROJECT=100.0
DIGITAL_HUMAN_COST_PER_SEC=0.5
VIDEO_GEN_COST_PER_SEC=1.0
GEN_CLIP_SECONDS=5.0
TTS_CHARS_PER_SEC=4.0

# ---------- 视频合成（模块三）----------
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
VIDEO_WIDTH=1920
VIDEO_HEIGHT=1080
VIDEO_FPS=30
SLIDE_FONT_PATH=

# ---------- 认证 / JWT ----------
JWT_SECRET_KEY=你生成的64位随机密钥        ← 🔴 必填
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ---------- 网络代理 ----------
# 国内网络访问智谱/Resend 可能需要代理，留空直连
HTTP_PROXY=

# ---------- 视频水印 ----------
WATERMARK_TEXT=
WATERMARK_IMAGE_PATH=
WATERMARK_OPACITY=0.3

# ---------- AI 全自动生成 ----------
AI_FULL_GEN_DEFAULT=false
SILENT_SCENE_DURATION=4.0

# ---------- 流水线 ----------
SKIP_REVIEW=false

# ---------- 邮件验证码 ----------
RESEND_API_KEY=                          ← 🟡 推荐（需注册功能时填写）
EMAIL_FROM=EduCast <noreply@yourdomain.com>  ← 🟡 推荐（需注册功能时填写）
VERIFICATION_CODE_EXPIRE_MINUTES=10
VERIFICATION_CODE_COOLDOWN_SECONDS=60
VERIFICATION_CODE_MAX_ATTEMPTS=5
```

> 完整注释版模板见 [`.env.example`](.env.example)。

#### 生成 JWT_SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

将输出的 64 位十六进制字符串填入 `.env`。**不配置将导致系统拒绝启动。**

#### 获取智谱 API Key

在 [open.bigmodel.cn](https://open.bigmodel.cn) 注册，获取 API Key。GLM-4.7-Flash 为**免费**模型，用于 LLM 脚本编排和 CogVideoX 视频生成。

### 全部环境变量参考

| 分类 | 变量 | 说明 | 默认值 |
|------|------|------|--------|
| **必填** | `JWT_SECRET_KEY` | JWT 签名密钥（启动时不可为空） | — |
| **LLM** | `ZHIPU_API_KEY` | 智谱 API 密钥（GLM-4.7-Flash 免费） | — |
| **LLM** | `ZHIPU_MODEL` | 模型名称 | `glm-4.7-flash` |
| **LLM** | `ZHIPU_BASE_URL` | API 地址 | `https://open.bigmodel.cn/api/paas/v4` |
| **LLM** | `LLM_TIMEOUT` | LLM 请求超时（秒） | `60.0` |
| **视频生成** | `COGVIDEO_API_KEY` | CogVideoX 密钥（留空则回退用 ZHIPU_API_KEY） | — |
| **视频生成** | `COGVIDEO_MODEL` | 模型名称 | `cogvideox-flash` |
| **视频生成** | `VIDEO_GEN_TIMEOUT` | 视频生成请求超时（秒） | `300.0` |
| **视频生成** | `VIDEO_GEN_POLL_INTERVAL` | 轮询间隔（秒） | `5.0` |
| **TTS** | `EDGE_TTS_VOICE` | Edge TTS 音色 | `zh-CN-XiaoxiaoNeural` |
| **数字人** | `DIGITAL_HUMAN_API_KEY` | 数字人 API 密钥（不配则本地画中画兜底） | — |
| **数字人** | `DIGITAL_HUMAN_AVATAR_NAME` | 兜底讲师姓名条文本 | `AI 讲师` |
| **邮件** | `RESEND_API_KEY` | Resend 邮件 API 密钥（注册验证码） | — |
| **邮件** | `EMAIL_FROM` | 发件人地址（需 Resend 验证域名） | `EduCast <noreply@yourdomain.com>` |
| **邮件** | `VERIFICATION_CODE_EXPIRE_MINUTES` | 验证码有效期（分钟） | `10` |
| **邮件** | `VERIFICATION_CODE_COOLDOWN_SECONDS` | 同邮箱重发冷却（秒） | `60` |
| **邮件** | `VERIFICATION_CODE_MAX_ATTEMPTS` | 最大验证尝试次数 | `5` |
| **数据库** | `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./educast.db` |
| **存储** | `STORAGE_ROOT` | 文件存储根目录 | `./storage` |
| **CORS** | `CORS_ORIGINS` | 允许的前端来源 | `["http://localhost:5173"]` |
| **网络** | `HTTP_PROXY` | HTTP 代理地址（留空直连） | — |
| **认证** | `JWT_ALGORITHM` | JWT 签名算法 | `HS256` |
| **认证** | `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期（分钟） | `15` |
| **认证** | `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 有效期（天） | `7` |
| **视频** | `VIDEO_WIDTH` / `VIDEO_HEIGHT` | 输出分辨率 | 1920×1080 |
| **视频** | `VIDEO_FPS` | 输出帧率 | `30` |
| **视频** | `FFMPEG_BIN` / `FFPROBE_BIN` | FFmpeg 可执行路径 | `ffmpeg` / `ffprobe` |
| **水印** | `WATERMARK_TEXT` | 可见水印文本（留空用课程标题） | — |
| **水印** | `WATERMARK_IMAGE_PATH` | 图片水印路径（可选） | — |
| **水印** | `WATERMARK_OPACITY` | 水印透明度 0.0~1.0 | `0.3` |
| **流水线** | `SKIP_REVIEW` | 跳过人工审核直出成片 | `false` |
| **流水线** | `AI_FULL_GEN_DEFAULT` | AI 全自动生成模式 | `false` |
| **流水线** | `SILENT_SCENE_DURATION` | 无声分镜兜底时长（秒） | `4.0` |
| **成本** | `MAX_COST_PER_TASK` | 单任务最大成本（元） | `10.0` |
| **成本** | `MAX_COST_PER_PROJECT` | 单项目最大成本（元） | `100.0` |
| **成本** | `DIGITAL_HUMAN_COST_PER_SEC` | 数字人费率（元/秒） | `0.5` |
| **成本** | `VIDEO_GEN_COST_PER_SEC` | 视频生成费率（元/秒） | `1.0` |
| **字体** | `SLIDE_FONT_PATH` | 课件页渲染字体（留空自动探测） | — |

完整模板见 [`.env.example`](.env.example)。

---

## 启动服务

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端地址：http://localhost:8000  
API 文档：http://localhost:8000/docs

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端地址：http://localhost:5173

### 默认管理员

首次启动自动创建：

- 用户名：`admin`
- 密码：`admin123456`

### 开发命令速查

| 命令 | 说明 |
|------|------|
| `cd backend && uvicorn app.main:app --reload --port 8000` | 启动后端（热重载） |
| `cd frontend && npm run dev` | 启动前端（热重载） |
| `cd backend && pytest tests/ -v` | 运行后端测试 |
| `cd frontend && npx tsc --noEmit` | TypeScript 类型检查 |
| `cd backend && black backend/` | Python 代码格式化 |
| `cd backend && ruff check backend/` | Python 代码检查 |
| `cd frontend && npx eslint src/` | TypeScript 代码检查 |
| `cd frontend && npx prettier --write src/` | TypeScript 代码格式化 |

---

## 运行时配置（Web 界面）

管理员登录后，可通过 **「系统设置」→「API Key 配置」** 页面动态管理密钥，**无需重启服务**。

### 功能一览

| 功能 | 说明 |
|------|------|
| **查看配置状态** | 列表展示每个 Key 的已配置/未配置状态 |
| **编辑 Key** | 填写或修改 API Key 值并保存 |
| **连通性检测** | 对每个 Key 发起最小化 API 探测，实时验证是否有效 |
| **运行时优先** | Web 界面保存的 Key 优先级高于 `.env` 文件 |

### 可管理的配置项

| 配置项 | 检测方式 | 说明 |
|--------|----------|------|
| 智谱 API Key | 发送 `max_tokens=10` 的聊天请求 | GLM-4.7-Flash + CogVideoX 通用 |
| CogVideoX Key | 发送最小化视频生成请求 | 认证 + 模型权限验证 |
| Resend 邮件 Key | 调用 GET /me 管理端点 | 受限 Key 也会正确识别 |
| 数字人 API Key | 格式检查（≥8字符） | 无通用探测接口，生成时自动生效 |
| 邮件发件人地址 | 格式校验（含 @） | 必须是 Resend 验证过的域名 |

### 连通性检测结果解读

| 结果 | HTTP 状态 | 含义 |
|------|-----------|------|
| ✅ 有效 | 200 | API 连通正常 |
| ✅ 有效 | 400 / 422 | 认证通过（请求参数问题不影响 Key 有效性） |
| ✅ 有效 | 429 | Key 有效，被 API 限流（等待 1-2 分钟后重试） |
| ❌ 无效 | 401 | 认证失败，Key 错误或已过期 |
| ❌ 无效 | 403 | 权限不足，Key 未开通对应服务 |
| ⚠️ 网络错误 | 超时/连接失败 | 检查网络、代理、防火墙 |

> 数据存储位置：`backend/storage/_runtime_settings.json`

---

## 特殊配置

### 网络代理

国内网络环境下，访问智谱 / Resend 等境外 API 可能需要代理。在 `.env` 中配置：

```ini
HTTP_PROXY=http://127.0.0.1:7890
```

- 支持 Clash (`7890`)、V2Ray (`10809`) 等常见代理工具
- 留空则不使用代理，直接连接
- 对所有外部 HTTP 请求生效（API 调用、邮件发送等）

### SSL 证书验证

生产环境使用完整的 SSL 证书校验。开发环境若遇到证书问题，**请配置正确的代理而非禁用 SSL**。

### 认证配置

| 场景 | 配置项 | 建议值 |
|------|--------|--------|
| 开发调试 | `ACCESS_TOKEN_EXPIRE_MINUTES` | 默认 15 分钟 |
| 长期会话 | `REFRESH_TOKEN_EXPIRE_DAYS` | 默认 7 天 |
| 演示模式 | `SKIP_REVIEW=true` | 跳过脚本审核自动生成 |
| AI 全生成 | `AI_FULL_GEN_DEFAULT=true` | 所有分镜由 CogVideoX 生成 |

### 成本护栏

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MAX_COST_PER_TASK` | ¥10.00 | 单次生成任务上限 |
| `MAX_COST_PER_PROJECT` | ¥100.00 | 单项目累计上限 |

> 超限时系统拒绝提交，防止意外扣费。**优先使用免费档模型（GLM-4.7-Flash / CogVideoX-Flash）可零成本运行。**

### Provider 降级链

外部 API 失败时自动降级，保证视频仍可产出：

```
LLM:       智谱 GLM-4.7-Flash → 本地轻量规整
TTS:       Edge TTS（免费）
数字人:     外部 API → 本地画中画兜底
视频生成:   CogVideoX → Placeholder
公式动画:   manim → matplotlib 图片降级
```

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
│   │   │   ├── upload.py       # 文件上传 & 解析 & 批量上传
│   │   │   ├── scripts.py      # 脚本编辑 & LLM 编排
│   │   │   ├── tasks.py        # 任务流水线
│   │   │   ├── resources.py    # 资源管理
│   │   │   ├── settings.py     # 运行时配置（API Key 管理）
│   │   │   ├── monitoring.py   # 系统监控
│   │   │   ├── annotations.py  # 视频标注 CRUD
│   │   │   ├── templates.py    # 模板市场
│   │   │   ├── websocket.py    # WebSocket 进度推送
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
│   │   ├── middleware/         # 认证中间件 & 访问日志
│   │   └── utils/              # 工具函数 (FFmpeg, JSON, Hash, TaskHelpers)
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
│       │   ├── Upload/         # 上传 & 解析 & 批量上传
│       │   ├── ScriptEditor/   # 脚本编辑器
│       │   ├── Workspace/      # 工作空间
│       │   ├── Preview/        # 视频预览
│       │   ├── Resources/      # 资源管理
│       │   ├── KnowledgeGraph/  # 知识图谱可视化
│       │   ├── Assessment/     # 随堂测试
│       │   ├── Analytics/      # 学情分析看板
│       │   ├── TemplateMarket/ # 模板市场
│       │   ├── Monitoring/     # 系统监控
│       │   ├── Settings/       # 系统设置（API Key 配置）
│       │   └── Admin/          # 管理后台
│       ├── stores/             # Zustand 状态管理
│       ├── hooks/              # 自定义 Hooks (WebSocket)
│       ├── types/              # TypeScript 类型定义
│       └── styles/             # 全局样式
├── .env.example                # 环境变量模板
├── start.bat                   # Windows 一键启动脚本
└── AGENTS.md                   # AI 开发助手指引
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19, TypeScript, Vite, Ant Design, ECharts, Zustand, Axios |
| 后端 | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, slowapi |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 认证 | JWT (python-jose), bcrypt, HttpOnly Cookie |
| 实时通信 | WebSocket (原生) |
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
| **P6** | 安全加固 + 功能扩展：批量上传、WebSocket、标注、模板市场、学情分析 | ✅ |

## License

MIT
