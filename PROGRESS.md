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

## 📝 接下来待办 (Next Steps)

接下来，我们将进入 **P1 核心功能实现阶段**，重点打通文件解析到最终合成的数据流：

1. **[后端] 文档解析功能 (`pipeline/parser.py`)**
   - 优先实现 PPTX 解析 (`python-pptx`)：提取文本、图片，并组装为初版 IR（中间表示）。
2. **[后端] 大模型脚本编排 (`providers/llm` & `pipeline/scriptwriter.py`)**
   - 接入智谱 GLM-4-Flash，编写 Prompt，将初版 IR 扩写为包含分镜、口播词、字幕的详细脚本。
3. **[后端] TTS 配音 (`providers/tts`)**
   - 接入 Edge-TTS，根据分镜中的口播词生成对应的旁白音频文件。
4. **[后端] FFmpeg 视频合成 (`utils/ffmpeg.py` & `pipeline/composer.py`)**
   - 将背景图、配音音频、字幕通过代码组装 FFmpeg 命令，合成为最终的 MP4 视频。
5. **[前端] 联调与状态反馈**
   - 前端真实调用上传接口，并展示任务流转状态（Parsing -> Scripting -> Composing）。
   - 解析完成后，在脚本编辑器中呈现真实的 IR 数据供用户审核/修改。
