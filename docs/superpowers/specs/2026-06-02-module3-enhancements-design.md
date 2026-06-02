# 模块三增强设计：课件真实渲染 · 成本护栏 · 一键全自动

> 日期：2026-06-02 ｜ 状态：已与用户确认，待转实施计划
> 背景：模块三（教学视频生成与合成引擎）已落地最小闭环并提交（commit 855f107）。
> 本设计在其上做三项增强，均为独立特性，建议按 ①→②→③ 顺序实现。

## 目标与动机

| # | 增强 | 解决的问题 | 对应需求 |
|---|---|---|---|
| ① | 课件页真实渲染 | 解析器只写占位 `slide_ref`，底图全靠 Pillow 文本合成，无法还原 PPT/PDF 原版式 | 5.1 图表关联 / 5.3 A 课件页渲染 |
| ② | 成本估算 + 配额护栏 + 监控面板 | `Task.estimated/actual_cost`、配额配置都在但无人执行；模块 4/5 接付费 API 易超支 | 7.7 成本护栏 / 5.5 监控面板 / 13.4 答辩亮点 |
| ③ | 一键全自动 `SKIP_REVIEW` | 当前必须人工 `approve` 才生成，演示不便 | 8.3 演示 / 6 可用性 |

## 全局约束（三项共同遵守）

- **无新 Python 依赖**：PyMuPDF(fitz) 已在 requirements（此前仅声明未用）；LibreOffice 不强制安装。
- **无数据库 Schema 改动**：复用 `Task.estimated_cost/actual_cost`；项目级花费与存储用量用查询聚合。
- 沿用既有「服务 → 后台任务(独立 session) → 状态推进 + 降级」范式与 mock 测试策略（单测不依赖真实 ffmpeg / 网络 / LibreOffice）。
- 外部能力一律走 Provider 适配层；不硬编码密钥。

---

## ① 课件页真实渲染（PDF 真页图 + PPTX 优雅降级）

**原则**：能拿到真实页图就用真实页图作底，拿不到就维持现有文本合成（降级保证任何输入都出片）。

### 组件
- **新增 `app/pipeline/slide_raster.py`**（纯工具，可独立测试）：
  - `rasterize_pdf(pdf_path, out_dir, *, prefix="page", zoom=2.0) -> list[str]`：用 fitz 逐页渲染为 `{prefix}_{n}.png`，返回路径列表。
  - `find_soffice() -> str | None`：探测 LibreOffice（PATH + 常见安装目录）。
  - `pptx_to_pdf(pptx_path, out_dir) -> str | None`：`soffice --headless --convert-to pdf`；无 soffice 返回 None。
- **`app/pipeline/parser.py`**：
  - `ParsedSlide` 增加 `background_path: str = ""`。
  - `_parse_pdf`：用 fitz 栅格化整页 → `background_path`；顺带用 `page.get_images` 真正提取内嵌图修复当前"空写 image_paths"的 bug。
  - `_parse_pptx`：`find_soffice()` 命中则 `pptx_to_pdf → rasterize_pdf` 按页序映射到各 slide 的 `background_path`；否则留空。
  - `_slides_to_knowledge_points`：`VisualSpec.slide_ref = s.background_path or f"slide_{page}.png"`（有真实页图则填绝对路径）。
- **`app/pipeline/renderer.py`**：`render_scene` 增参 `background_path: str | None`。
  - 命中真实页图：缩放铺满 1920×1080（contain + 白边居中）作底，仅叠**字幕条 + 水印 + 角标**，跳过标题/正文合成。
  - 未命中：现有文本合成路径不变。
- **`app/services/composition_service.py`**：把 `scene.visual_spec.slide_ref` 在 `os.path.exists` 为真时作为 `background_path` 传入 `render_scene`。

### 数据流
`PDF/PPTX → 解析(fitz/soffice 栅格化) → slide_ref=真实页图路径 → 合成时 render_scene 以真页图作底 → 成片`

### 降级
真实页图 →（无 soffice / 非 PDF/PPTX）→ Pillow 文本合成。

### 测试
- `test_slide_raster.py`：用 tests 已有最小 PDF 字面量跑 `rasterize_pdf`，断言 PNG 存在且尺寸>0；`find_soffice` 返回类型。
- `test_renderer.py`：新增 background 分支（传入生成的 PNG，输出 1080p 且字幕仍叠加）。
- `test_parser*`：PDF 解析后 `slide_ref` 指向存在的真实文件。

---

## ② 成本估算 + 配额护栏 + 监控面板

### 组件
- **Provider 估价补全**：`providers/digital_human/placeholder.py`、`providers/video_gen/placeholder.py` 实现 `estimate_cost`，按 `settings.DIGITAL_HUMAN_COST_PER_SEC` / `VIDEO_GEN_COST_PER_SEC` × 预估时长给出非零估算（真实 API 未接也有可信预估）。
- **新增 `app/services/cost_service.py`**：
  - `estimate_ir_cost(ir, config=None) -> CostEstimate`：展平分镜，按 `scene_type` 路由到对应 provider 估价（slide/formula=0；digital_human/generative 按"旁白字数→预估秒数×费率"）。返回总额 + 分类明细。
  - `async check_quota(db, project_id, estimated)`：`已花费 = Σ Task.actual_cost(该项目)`；`estimated > MAX_COST_PER_TASK` 或 `已花费 + estimated > MAX_COST_PER_PROJECT` → 抛 `CostLimitException`（全局处理器 → 429）。
  - `async project_cost_summary(db, project_id) -> CostSummary`：任务按状态计数、累计 estimated/actual、存储用量 = `Σ Resource.file_size`。
  - `async dashboard_stats(db) -> DashboardStats`：全局任务状态分布、累计成本、存储、最近任务。
- **Schemas（`app/schemas/cost.py`）**：`CostEstimate`（total + breakdown[]）、`CostSummary`、`DashboardStats`。
- **接线**：
  - `api/v1/scripts.py::approve_script`：生成前 `est = estimate_ir_cost(ir)` → `task.estimated_cost = est.total` → `check_quota`（超额 429，不启动）→ 启动合成。
  - `services/composition_service.py`：结束时 `task.actual_cost = Σ subtask.cost`（模块三为 0，机制就位）。
- **API（新增 `app/api/v1/monitoring.py`）**：
  - `GET /projects/{id}/cost-estimate` — 审核前对最新 IR 预估。
  - `GET /projects/{id}/cost` — 项目成本/存储汇总。
  - `GET /monitoring/dashboard` — 全局聚合（答辩监控面板数据源）。

### 不改 DB
复用 `Task.estimated_cost/actual_cost`；项目级花费 `Σ Task.actual_cost`、存储 `Σ Resource.file_size` 均查询求和。

### 测试
- `test_cost_service.py`：估算（注入费率，digital_human/generative 非零）、配额通过 / 超 task / 超 project 抛 `CostLimitException`、汇总聚合正确。
- `test_monitoring_api.py`：三个端点返回结构；`approve` 超额 → 429。

---

## ③ 一键全自动 `SKIP_REVIEW`

### 组件
- **`app/config.py`**：`SKIP_REVIEW: bool = False`。
- **`app/api/v1/upload.py` `_run_parse_in_background`**：`orchestrate` 完成（reviewing）后，若 `settings.SKIP_REVIEW`：
  1. `est = estimate_ir_cost(ir)`；`check_quota`（超额 → 任务停在 failed，不生成）。
  2. `task.estimated_cost = est.total`，`CompositionService().compose(...)` 推进到 completed。
- 默认 False → 保持人在环，与现有行为一致。

### 测试
- `test_skip_review.py`：monkeypatch `CompositionService.compose` 为探针 —— `SKIP_REVIEW=True` 时被调用、False 时不调用（不重测合成本身）。

---

## 实施顺序与依赖
1. **①** 渲染保真（独立）。
2. **②** 成本护栏（被 ③ 复用；先于 ③）。
3. **③** 自动模式（依赖 ② 的 estimate/check_quota）。

每步 TDD：先/同步写测试 → 实现 → `pytest` 全绿 + `ruff`/`black` → 提交（Conventional Commits）。

## 验证
- `pytest tests/ -v` 全绿（含已有 112 项 + 新增）。
- 端到端：装/不装 LibreOffice 两种情况各跑一次上传→成片，确认 PDF 用真页图、PPTX 无 soffice 时降级文本合成。
- `GET /monitoring/dashboard` 与 `/projects/{id}/cost` 返回合理数据；`approve` 在调低 `MAX_COST_PER_PROJECT` 时返回 429。
- `SKIP_REVIEW=True` 上传一个 .md → 自动出片。

## 风险与对策
| 风险 | 对策 |
|---|---|
| LibreOffice 转换慢/不稳 | 仅 PPTX 用，且可选；失败/缺失即降级文本合成，不阻断 |
| fitz 栅格化大文件耗时/内存 | zoom 限 2.0；按页处理；异常降级 |
| placeholder 费率与真实 API 偏差 | 费率走 settings 可调；答辩口径明确为"预估"，actual_cost 以真实调用为准 |
| 自动模式下超额静默 | 自动路径同样 check_quota，超额置 failed 并记 error_message |
