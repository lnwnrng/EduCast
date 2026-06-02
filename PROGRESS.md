# 课影 (EduCast) — 开发进度与待办事项

## ✅ 已完成 (P1 骨架搭建阶段)

截至目前，我们已经成功跑通了课影 (EduCast) 项目的全栈骨架，具体完成的内容如下：

### 1. 基础设施
- [x] **目录结构初始化**：前端 `frontend/` 与后端 `backend/` 隔离架构。
- [x] **根目录配置**：创建了 `.gitignore`、`.env.example` 和项目概述的 `README.md`。
- [x] **版本控制**：Git 仓库初始化与首批代码规范设定。

### 2. 后端核心层 (Python / FastAPI)
- [x] **虚拟环境与依赖**：创建了 `.venv`，集成了 FastAPI, SQLAlchemy, Alembic, Pydantic, edge-tts, FFmpeg 抽象等。
- [x] **数据库与模型**：
  - 配置了异步 SQLite (`aiosqlite`)。
  - 完成了四大核心模型定义：`Project`（项目）、`Task` / `SubTask`（任务状态机）、`Resource`（教学资源）。
- [x] **API 路由与业务逻辑**：
  - 实现了标准 CRUD 的 Services 层与 FastAPI V1 路由。
  - Pydantic Schema 类型已对齐，修复了 UUID 序列化的问题。
- [x] **核心功能模块骨架**（预留了接口与空实现）：
  - **IR 层**：基于文档设计的四层课程脚本数据结构（Course -> Chapter -> KnowledgePoint -> Scene）。
  - **Provider 适配层**：统一了 LLM、TTS、数字人、视频生成的调用规范，实现了带有降级链的 Router，并写好了免费方案（智谱/Edge-TTS）的空接口。
  - **Pipeline 层**：定义了串联文档解析、脚本编排、素材生成、视频合成的任务状态机。
- [x] **测试通过**：后端基础自动化测试 (`pytest`) 已跑通。

### 3. 前端表现层 (React / Vite)
- [x] **项目初始化**：基于 Vite + React + TypeScript 构建，配置了开发环境的 API 代理。
- [x] **核心依赖安装**：Ant Design, Zustand, React Router, Axios, React Query。
- [x] **全局状态与网络通信**：配置了全局样式、Zustand 侧边栏状态、Axios 请求拦截器及统一定义的 TypeScript 接口。
- [x] **页面骨架实现**（带 AntD 布局）：
  - **Dashboard**（仪表盘）：系统概览与最近任务统计。
  - **Upload**（课件上传）：拖拽上传与解析步骤展示。
  - **ScriptEditor**（脚本编辑器）：分镜列表与内容编辑面板。
  - **Preview**（成片预览）：视频播放器占位与章节导航。
  - **Resources**（资源管理）：表格化的素材与成片管理。


---

## 📝 接下来待办 (核心功能开发清单)

为了确保功能完整对应《需求分析文档》中的 6 大核心模块，接下来的开发将分模块逐步推进，您可以按顺序逐一实现并进行测试：

### 模块一：课件解析引擎 (Parser Module)
- [x] **解析服务 (`pipeline/parser.py`)**：完整实现 PPTX（python-pptx: 标题/正文/备注/图片提取, 章节自动检测）、PDF（pdfplumber: 逐页文本/大号标题检测）、Markdown（标题层级拆分章节/知识点）、纯文本（段落切分）四种解析器。
- [x] **IR 构建**：实现 slide → scene 映射、章节自动切分、知识点分组，生成标准四层 CourseIR 结构（草稿态）。
- [x] **解析服务层 (`services/parser_service.py`)**：协调解析 + IR 保存到文件系统 + Task/Project 状态更新 + 多版本 IR 管理。
- [x] **上传 API 增强 (`api/v1/upload.py`)**：上传后自动创建 Project + Task，通过 BackgroundTasks 触发后台解析。
- [x] **脚本 API 实现 (`api/v1/scripts.py`)**：实现 IR 加载（get_script）和更新（update_script, 含版本管理与校验）。
- [x] **单元测试与集成测试 (73 tests all passing)**：覆盖 IR Schema、IR 校验器、四种解析器、解析服务 IR 持久化、上传 API、脚本 API。
- [x] **前端交互**：完善 Upload 页面（三步向导：上传→解析轮询→结果校对），ScriptEditor 页面（加载真实 IR、章节/知识点/分镜树形浏览、分镜编辑表单、保存/审核），新增 upload.ts / scripts.ts API 层。

### 模块二：大模型脚本编排 (LLM Scriptwriter Module)
- [ ] **LLM Provider 接入 (`providers/llm/zhipu.py`)**：使用智谱 GLM-4-Flash API，实现 `generate_script` 接口封装。
- [ ] **编排逻辑 (`pipeline/scriptwriter.py`)**：编写结构化 Prompt，将第一版 IR 输入给大模型，生成包含分镜（数字人/课件页/生成式画面）、口播讲稿、字幕文本及时间预估的详细版 IR。
- [ ] **前端审核**：在 `ScriptEditor` 页面完整渲染 IR 数据，允许教师进行图文、口播词及画面类型的二次调整并保存。

### 模块三：基础渲染与合成 (Renderer & Composer Module)
- [ ] **TTS 配音生成 (`providers/tts/edge_tts_provider.py`)**：解析 IR 中的 `narration_text`，批量请求 Edge-TTS 生成音频，并获取时长。
- [ ] **课件静态渲染**：根据 IR 分镜指定的课件页（或背景色），生成静态背景图片或视频片段。
- [ ] **FFmpeg 最终合成 (`utils/ffmpeg.py` & `pipeline/composer.py`)**：基于时间轴，将音频、背景图、通过 `srt` 生成的字幕组装成复杂的 FFmpeg Filtergraph 命令，输出最终的 MP4。

### 模块四：数字人集成 (Digital Human Module)
- [ ] **Provider 抽象设计**：针对腾讯云/硅基等第三方数字人 API 设计适配器接口。
- [ ] **降级方案实现**：为了解决初期零预算问题，实现一个“占位”或“纯静态图+动嘴”的本地数字人 mock 方案。
- [ ] **流水线整合**：当分镜为 `digital_human` 时，触发该任务节点，生成带 Alpha 通道或绿幕的口播视频，交由 FFmpeg 叠加。

### 模块五：生成式教学片段 (Generative Clip Module)
- [ ] **生成 API 接入 (`providers/video_gen`)**：预留 Sora/可灵等视频生成 API 的适配逻辑，或调用免费的文生图 API 生成概念图片。
- [ ] **自动配图逻辑**：针对“抽象概念引入”等分镜，自动提取关键词，调用外部 API 产生视觉素材并无缝插入视频时间轴。

### 模块六：教学评估与增强 (Assessment & Enhancement Module) 
*(视进度与答辩需求选做)*
- [ ] **课后题库生成**：基于最终的 IR，利用 LLM 针对每个知识点生成包含单选、多选、解析的随堂测验。
- [ ] **公式与代码动画**：尝试接入 `manim`，对于数学公式推导或代码讲解分镜，生成程序化动画视频替代静态课件。
- [ ] **打包导出**：提供将视频、字幕、试题打包为标准归档包（如 ZIP）供用户下载的功能。
