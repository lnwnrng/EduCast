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

> **本轮（P2，2026-06-03）完成**：模块四（Provider 抽象 + 本地讲师画中画兜底）、模块五（智谱 **CogVideoX-Flash** 真机，复用现有 `ZHIPU_API_KEY`）、**公式渲染**（manim 优先 + matplotlib 图片显影兜底）。后端 **166 tests 全绿**、ruff/black 干净，前端 tsc/eslint/build 绿；真机 CogVideoX 出片 + 端到端四类分镜合成均已验证。已 commit `2069b2b`。
>
> **剩余（按需选做，未排期）**：模块六「题库」独立前端页与导出；（选）数字人**云端真机**接入（已选型，见模块四注）；（选）manim 真机渲染（装 MiKTeX 后 `FORMULA_ENGINE=auto` 自动启用）。

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

### 模块四：数字人集成 (Digital Human Module) ✅（抽象层 + 本地兜底；云端真机已选型待接）
> 本轮交付 **Provider 抽象 + 本地「讲师画中画」零成本兜底**；云端真机本轮**先不接**（已选型，留作热插拔适配器）。
>
> **推荐真机方案（已调研）**：阿里百炼 **wan2.2-s2v**（图片+音频→真对口型；新用户**免费 100 秒**，之后 480P 0.5元/秒、720P 0.9元/秒；DashScope 异步 REST `POST .../aigc/image2video/video-synthesis` + 头 `X-DashScope-Async: enable` → 轮询 `GET /tasks/{id}`，状态 PENDING/RUNNING/SUCCEEDED/FAILED，取 `output.results.video_url`）——正好吃我们逐镜现成的 TTS 旁白音频做口型同步。论文可加 **开源自建（HeyGem 需 ≥8–12G 显存 / MuseTalk + 免费 GPU 笔记本 Kaggle·魔搭）** 作"自建 vs 云 API"对比实验。HeyGen 2026-02 起取消免费 API、性价比差，不推荐。
> 接入只需加 `providers/digital_human/<vendor>.py` 实现 `BaseProvider` + 本地文件转临时公网 URL 上传（百炼自带临时上传），**合成层与成本护栏零改动**（计费随 `DIGITAL_HUMAN_API_KEY` 自动生效）。
- [x] **Provider 抽象设计**：复用 `BaseProvider`（`submit/poll/get_result/estimate_cost`）。`providers/digital_human/__init__.py: get_digital_human_provider()` 按 `DIGITAL_HUMAN_API_KEY` 切换云端/兜底（本轮云端恒 None）；新增 vendor Provider 即热插拔，合成层与成本护栏零改动（计费已随 Key 自动生效）。
- [x] **本地兜底实现 (`providers/digital_human/local.py`)**：`LocalDigitalHumanProvider.render_foreground` + `renderer.render_avatar` 渲染透明底讲师头像卡（字母徽章 + 姓名条 + 「讲解中」药丸），由 `overlay_pip_clip` 叠加为画中画（静态前景加轻微浮动动感，非真口型——诚实占位）。
- [x] **流水线整合 (`composition_service._build_digital_human`)**：`digital_human` 分镜渲染课件底图 + 讲师前景 → `ffmpeg.overlay_pip_clip`（按 IR `pip_position/pip_size` 定位/缩放，支持四角/全屏）；前端「数字人讲师」开关（默认开、免费）。任一步失败降级纯课件页 + 旁白。

### 模块五：生成式教学片段 (Generative Clip Module) ✅（CogVideoX 真机 + 运镜兜底）
> 接入**智谱 CogVideoX-Flash**（与 GLM 同平台同 Key，async REST）；无 Key/未开启/失败时降级为「概念图 Ken-Burns 运镜」。
- [x] **生成 API 接入 (`providers/video_gen/cogvideox.py`)**：`CogVideoXProvider` 实现 `POST /videos/generations` → 轮询 `GET /async-result/{id}`（PROCESSING/SUCCESS/FAIL，带超时退避）→ httpx 下载 mp4 的 `generate()`。`get_video_gen_provider()` 优先 `COGVIDEO_API_KEY`、为空回退 `ZHIPU_API_KEY`；flash 档计费 0、正式档按时长 × 费率。
- [x] **流水线整合 + 缓存 (`composition_service._build_generative`)**：`generative_clip` 分镜按 `gen_prompt` 生成（`sha256(模型+提示词)` 命中 `storage/_cache/video_gen` 复用，避免重复付费）→ `video_audio_to_clip` 归一化并叠加旁白（旁白更长则循环补足）；未开启/无 Key/失败 → 概念底图 `image_to_kenburns_clip` 运镜兜底。前端「生成式片段」开关 + 成本预估透传（仅开启且配 Key 才计费）。

### 模块六：教学评估与增强 (Assessment & Enhancement Module) ✅
*(视进度与答辩需求选做)*
- [x] **课后题库生成**：模块二的 LLM 编排已为每个知识点生成 `quiz_seeds`（题干/题型/答案/解析）并入 IR；**已完成**：独立的「随堂测试」前端页（选择题/填空题/简答题/计算题，支持随机打乱、提交评分、答案解析展示）。
- [x] **公式渲染画面 (`pipeline/formula.py`)**：`FormulaRenderer` **manim 优先 + 自动降级**——`FORMULA_ENGINE=auto` 时探测 `manim`+系统 LaTeX 可用则逐行 `Write`/`Indicate` 推导；否则走**纯 pip 图片显影**（matplotlib mathtext 把每步渲染为 PNG，按「累计展示前 k 行、第 k 行高亮」拼显影视频，CJK 字体复用课件渲染器探测，非法 mathtext 退化纯文本）。`composition_service._build_formula` 用 `video_audio_to_clip` 叠加旁白（旁白驱动时长），空步骤/失败降级课件页。`renderer.render_formula_animation` 仍保留为最终静态兜底。
- [x] **打包导出**：模块三的 `composition_service` 已在出片时自动打包 **zip**（成片 + SRT + VTT + 封面 + IR 快照），并作为 `archive` 资源入库、可在资源管理/预览页下载。

---

## ✅ 已完成 (P4 功能增强阶段)

### 功能 1：多视频模板支持 ✅
- [x] **模板注册表 (`pipeline/templates.py`)**：定义 `TemplateConfig` dataclass（配色/prompt风格/分镜偏好/时长范围），内置微课（蓝白简约）、慕课（深蓝学术）、实验课（绿白活力）三种模板。
- [x] **SlideRenderer 模板配色**：构造函数接受 `template_name` 参数，从注册表读取配色覆盖类级别默认值（bg/accent/title/body/badge 等）。
- [x] **ScriptWriter 模板感知**：`_build_kp_messages` 读取 `ir.template` 注入模板专属 `prompt_style` 和 `scene_type_hint` 到 LLM system prompt。
- [x] **CompositionService 传递模板**：`compose()` 加载 IR 后根据 `ir.template` 重建 `SlideRenderer` 实例。
- [x] **前端模板选择 UI**：Upload 页面顶部新增 Segmented 卡片选择器（微课/慕课/实验课），上传时附带 `template` 参数。
- [x] **后端接收模板参数**：`upload.py` 新增 `template: str = Form("micro_lecture")`，创建 Project 时写入，ParserService 解析时从 Project 继承到 IR。

### 功能 2：知识图谱可视化 ✅
- [x] **后端 API**：`GET /projects/{id}/knowledge-graph` 从 IR 提取知识点节点和共享标签关联边。
- [x] **前端页面**：ECharts 力导向图渲染，节点按章节着色，点击节点显示详情抽屉（要点、标签）。
- [x] **路由导航**：Workspace 页面新增「知识图谱」按钮。

### 功能 3：随堂测试模块 ✅
- [x] **后端 API**：`GET /projects/{id}/assessment` 从 IR 提取随堂练习题按章节分组。
- [x] **前端测试页面**：支持选择题/填空题/简答题/计算题，随机打乱、提交评分、答案解析展示。
- [x] **路由导航**：Workspace 页面新增「随堂测试」按钮。

### 功能 4：视频水印 ✅
- [x] **FFmpeg 文字水印**：合成管线末尾使用 `drawtext` 滤镜在成片右下角添加半透明文字水印（课程标题或自定义文本）。
- [x] **配置项**：`WATERMARK_IMAGE_PATH`（可选图片水印）、`WATERMARK_OPACITY`（默认 0.3）。
- [x] **前端开关**：生成配置表单新增「视频水印」Switch，通过 `use_watermark` 配置项控制。

### 功能 5：资源版本对比 ✅
- [x] **后端 API**：`GET /projects/{id}/versions/compare?v1=N&v2=M` 对比两个 IR 版本的知识点差异（新增/删除/修改）。
- [x] **前端组件**：`VersionCompareModal` 支持版本选择、统计概览、新增/删除/修改知识点分类展示。
- [x] **导航入口**：Workspace 页面新增「版本对比」按钮（需 2+ 版本时启用）。
