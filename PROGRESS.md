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

### 模块二：大模型脚本编排 (LLM Scriptwriter Module) ✅
- [x] **LLM Provider 接入 (`providers/llm/zhipu.py`)**：用 httpx 接入智谱 **GLM-4.7-Flash**（免费档）chat/completions，实现 `chat()`（关闭混合思考、可选 JSON 输出）与统一 Provider 接口；`providers/llm/__init__.py` 提供 `get_llm_provider()` 工厂（无 Key 返回 None 以降级）。`ProviderResult` 扩展 `content`/token 字段；新增配置 `ZHIPU_MODEL`/`ZHIPU_BASE_URL`/`LLM_TIMEOUT`。
- [x] **编排逻辑 (`pipeline/scriptwriter.py`)**：逐知识点构造结构化 Prompt → 调用 LLM → 健壮 `extract_json`（`utils/json_parse.py`）解析 → 按 order **就地合并**回 IR（保留 scene_id/slide_ref/来源页）。产出：口语化讲稿、精炼字幕、画面类型重判、生成式 `gen_prompt`、公式 `latex_steps`、知识点标签、随堂练习题、课程元信息推断。含单点失败/无 Key 的降级兜底。`services/scriptwriter_service.py` 协调任务状态与 IR 版本；**上传解析后自动接续编排**（`upload.py`），并提供手动「重新编排」端点（`scripts.py: generate_script` 返回 task_id 供轮询）。
- [x] **前端审核**：`ScriptEditor` 新增「AI 重新编排」按钮（触发+轮询+重载）、课程元信息标签、生成式提示词编辑、公式步骤展示、随堂练习题区块。
- 测试：新增 `test_json_parse` / `test_scriptwriter`（注入 FakeLLM）/ `test_zhipu_provider`（httpx MockTransport），后端 **89 tests 全通过**，前端 vite 构建通过。

### 模块三：基础渲染与合成 (Renderer & Composer Module) ✅
- [x] **TTS 配音生成 (`providers/tts/edge_tts_provider.py`)**：实现 Edge-TTS 逐分镜配音（`synthesize` + 统一 Provider 接口 + `get_tts_provider` 工厂）；空旁白/失败降级为静音分镜，时长经 ffprobe 获取并驱动分镜。
- [x] **课件静态渲染 (`pipeline/renderer.py`, Pillow)**：从 IR 文本合成 1920×1080 课件页（标题/要点 + 字幕烤入画面 + 水印 + 画面意图角标，CJK 字体自动探测兜底）；**PDF 用 PyMuPDF 栅格化为真实页图作底、PPTX 有 LibreOffice 时转 PDF 后同样出真实页图**（`pipeline/slide_raster.py`），无则降级文本合成；封面卡渲染。
- [x] **字幕与章节 (`pipeline/subtitles.py`)**：SRT/VTT 生成 + FFmpeg 章节 metadata，时间轴由旁白音频时长累计驱动。
- [x] **FFmpeg 最终合成 (`utils/ffmpeg.py` & `pipeline/composer.py`)**：逐分镜「静图 + 音频 → 片段」→ concat demuxer 拼接 → 软字幕(mov_text) + 章节复用 → **`-movflags +faststart` 前置 moov，浏览器可流式播放/拖动**。
- [x] **合成编排服务 (`services/composition_service.py`)**：展平 IR → 逐镜渲染 + 配音（各记一条 SubTask）→ 合成 → 封面 → **zip 打包** → Resource 入库；单镜/配音失败均可降级。`approve_script` 人在环放行触发后台合成；新增 `GET /resources/{id}/download`（FileResponse + Range 流式）。
- [x] **成本护栏与监控 (`services/cost_service.py`, `api/v1/monitoring.py`)**：生成前成本预估区分**潜在成本 vs 实际计费**（仅配置了付费 API Key 的能力才计费）+ 配额拦截（超额 429）+ 项目/全局成本与存储汇总端点（`/projects/{id}/cost-estimate`、`/projects/{id}/cost`、`/monitoring/dashboard`）；`approve` 记 `estimated/actual_cost`。
- [x] **一键全自动 (`SKIP_REVIEW`)**：开启后上传即自动跨过人工审核直接出片（仍走成本护栏）；默认关闭保持人在环。
- [x] **前端接通**：新增「**监控面板**」页（任务状态分布/累计成本/存储用量/最近任务）；「视频生成」页展示成本预估（潜在/实计费 + 免费降级提示）；「**成片预览**」页用原生 `<video>` 真正在线播放成片 + 中文 VTT 字幕轨 + 项目资源下载；「**资源管理**」页接通后端（列表/类型筛选/弹窗预览/下载/删除）。
- 测试：新增 slide_raster / renderer / edge-tts / subtitles / composition / cost_service / monitoring / approve_quota / skip_review / ffmpeg 真机集成（断言 faststart）等，后端 **137 tests 全通过**，ruff/black 干净，前端 tsc/eslint/`npm run build` 全绿。
- 设计/计划文档归档于 `docs/superpowers/`（spec + 实施计划）。

### 模块四：数字人集成 (Digital Human Module)
> 🔧 已铺垫：占位 Provider 已实现按时长 × 费率的 `estimate_cost`；成本护栏会在配置 `DIGITAL_HUMAN_API_KEY` 后**自动**对数字人分镜计费并拦截超额——接真实 API 时无需改护栏代码。当前 `digital_human` 分镜在模块三降级为课件页渲染。
- [ ] **Provider 抽象设计**：针对腾讯云/硅基等第三方数字人 API 设计适配器接口（落地 `submit/poll/get_result`）。
- [ ] **降级方案实现**：为了解决初期零预算问题，实现一个“占位”或“纯静态图+动嘴”的本地数字人 mock 方案。
- [ ] **流水线整合**：当分镜为 `digital_human` 时，触发该任务节点，生成带 Alpha 通道或绿幕的口播视频，交由 FFmpeg 叠加（画中画）。

### 模块五：生成式教学片段 (Generative Clip Module)
> 🔧 已铺垫：占位 `video_gen` Provider 已实现按时长 × 费率的 `estimate_cost`；成本护栏会在配置 `COGVIDEO_API_KEY` 后自动对 `generative_clip` 分镜计费拦截。当前该类分镜在模块三降级为课件页渲染（含 `gen_prompt` 文本展示）。
- [ ] **生成 API 接入 (`providers/video_gen`)**：预留 Sora/可灵等视频生成 API 的适配逻辑，或调用免费的文生图 API 生成概念图片。
- [ ] **自动配图逻辑**：针对“抽象概念引入”等分镜，自动提取关键词，调用外部 API 产生视觉素材并无缝插入视频时间轴。

### 模块六：教学评估与增强 (Assessment & Enhancement Module) 
*(视进度与答辩需求选做)*
- [~] **课后题库生成**：模块二的 LLM 编排已为每个知识点生成 `quiz_seeds`（题干/题型/答案/解析）并入 IR；**待做**：独立的「题库」前端页与导出（题目筛选、按知识点浏览、导出文档）。
- [ ] **公式与代码动画**：接入 `manim` 对公式推导/代码讲解分镜生成程序化动画。当前 `formula_animation` 分镜降级为课件页文本展示（`renderer.render_formula_animation` 为占位）。
- [x] **打包导出**：模块三的 `composition_service` 已在出片时自动打包 **zip**（成片 + SRT + VTT + 封面 + IR 快照），并作为 `archive` 资源入库、可在资源管理/预览页下载。
