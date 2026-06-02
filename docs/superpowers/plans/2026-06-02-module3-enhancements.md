# 模块三增强 Implementation Plan

> **For agentic workers:** 用 superpowers:executing-plans 逐任务执行。步骤用 `- [ ]` 勾选。
> 设计依据：`docs/superpowers/specs/2026-06-02-module3-enhancements-design.md`

**Goal:** 给模块三加三项增强——课件真实渲染(PDF 真页图)、成本估算+配额护栏+监控面板、SKIP_REVIEW 一键全自动。

**Architecture:** 沿用「服务→后台任务→状态推进+降级」范式；新增能力均可降级、可 mock 测试；不改 DB schema、不加 Python 依赖。

**Tech Stack:** FastAPI / SQLAlchemy async / Pydantic v2 / PyMuPDF(fitz) / Pillow / pytest(asyncio auto)。

测试统一从 `backend/` 运行：`.venv/Scripts/python.exe -m pytest <path> -q`。

---

## 特性 ① 课件页真实渲染

### Task 1：slide_raster 工具（PDF 栅格化 + soffice 探测）
**Files:** Create `backend/app/pipeline/slide_raster.py`；Test `backend/tests/test_slide_raster.py`

- [ ] 写失败测试：`rasterize_pdf` 把 1 页 PDF 渲染为 PNG。用 `tests/test_parsers.py` 里那段最小 PDF 字面量（复制到本测试 fixture，写入 tmp 文件）→ 调用后断言返回 1 个路径、文件存在、PIL 打开尺寸>0。再测 `find_soffice()` 返回 `str | None`（不抛错）。
- [ ] 跑测试确认失败（模块/函数不存在）。
- [ ] 实现：
  - `rasterize_pdf(pdf_path, out_dir, *, prefix="page", zoom=2.0) -> list[str]`：`import fitz`；`doc=fitz.open(pdf_path)`；逐页 `page.get_pixmap(matrix=fitz.Matrix(zoom,zoom))`；`pix.save(out_dir/f"{prefix}_{i+1}.png")`；`os.makedirs(out_dir, exist_ok=True)`；返回路径列表。
  - `find_soffice() -> str | None`：`shutil.which("soffice") or shutil.which("soffice.exe")`，再探 `C:/Program Files/LibreOffice/program/soffice.exe` 等常见路径；都没有返回 None。
  - `pptx_to_pdf(pptx_path, out_dir) -> str | None`：`so=find_soffice()`；None 则返回 None；否则 `subprocess.run([so,"--headless","--convert-to","pdf","--outdir",out_dir,pptx_path],...)`（UTF-8/errors=replace，超时），返回生成的 `.pdf` 路径（存在才返回）。
- [ ] 跑测试确认通过。
- [ ] 提交：`feat(parser): 新增 slide_raster（PDF 栅格化 + LibreOffice 探测）`

### Task 2：解析器产出真实页图 background_path
**Files:** Modify `backend/app/pipeline/parser.py`；Test `backend/tests/test_parser_service.py`（或 test_parsers.py 增用例）

- [ ] 写失败测试：解析最小 PDF 后，第一个 scene 的 `visual_spec.slide_ref` 指向一个**存在的文件**（`os.path.exists` 为真），且位于 `storage/{pid}/slides/` 下。用临时 STORAGE_ROOT。
- [ ] 跑测试确认失败。
- [ ] 实现：
  - `ParsedSlide.__init__` 增 `background_path: str = ""` 字段。
  - `_parse_pdf`：解析后调用 `slide_raster.rasterize_pdf(file_path, self._get_slide_dir(project_id), prefix="page")`，按页索引把路径填到对应 `ParsedSlide.background_path`；用 `try/except` 包裹，失败仅 log、留空（降级）。保留 pdfplumber 取文本。
  - `_parse_pptx`：`pdf=slide_raster.pptx_to_pdf(file_path, tmpdir)`；命中则 `rasterize_pdf` 映射到各 slide `background_path`，否则留空。
  - `_slides_to_knowledge_points`：`VisualSpec(slide_ref=s.background_path or f"slide_{s.page_number}.png", image_refs=s.image_paths)`。
- [ ] 跑测试确认通过 + 跑既有 `test_parsers.py`/`test_parser_service.py` 不回归。
- [ ] 提交：`feat(parser): PDF/PPTX 解析产出真实页图作为 slide_ref`

### Task 3：渲染器支持真实页图作底
**Files:** Modify `backend/app/pipeline/renderer.py`；Test `backend/tests/test_renderer.py`

- [ ] 写失败测试：`render_scene(..., background_path=<生成的1280x720 PNG>, subtitle="字幕", output_path=out)` → 输出 1920×1080 PNG（真页图缩放铺满 + 字幕仍叠加）。再测 `background_path` 不存在时回退文本合成不崩。
- [ ] 跑测试确认失败（参数不存在）。
- [ ] 实现：`render_scene` 增 `background_path: str | None = None`。命中且文件存在：`Image.open` → `ImageOps.contain` 到 (W,H) → 居中贴到白底画布作 `img`；随后仅画 `_draw_subtitle` + 水印 +（可选 badge）；不画标题/正文。未命中走原路径。
- [ ] 跑测试确认通过。
- [ ] 提交：`feat(renderer): 支持真实课件页图作为底画面`

### Task 4：合成服务接入 background_path
**Files:** Modify `backend/app/services/composition_service.py`；Test `backend/tests/test_composition_service.py`

- [ ] 写失败测试：在现有 `test_compose_full_flow` 给某 scene 设一个真实存在的 `slide_ref`（tmp 下生成 PNG），断言合成成功（render 被调用、成片产出）；并加断言：当 slide_ref 存在时该 scene 仍出片。
- [ ] 跑测试确认失败/或调整。
- [ ] 实现：`_build_scene_clip` 计算 `bg = scene.visual_spec.slide_ref if scene.visual_spec.slide_ref and os.path.exists(scene.visual_spec.slide_ref) else None`，传 `render_scene(..., background_path=bg)`。
- [ ] 跑测试确认通过。
- [ ] 提交：`feat(composition): 命中真实页图时以其为底渲染分镜`

---

## 特性 ② 成本估算 + 配额护栏 + 监控面板

### Task 5：Provider 费率估价 + 配置
**Files:** Modify `backend/app/config.py`、`backend/app/providers/digital_human/placeholder.py`、`backend/app/providers/video_gen/placeholder.py`；Test `backend/tests/test_cost_service.py`（先建空文件，后续填）

- [ ] config 增：`DIGITAL_HUMAN_COST_PER_SEC: float = 0.5`、`VIDEO_GEN_COST_PER_SEC: float = 1.0`、`TTS_CHARS_PER_SEC: float = 4.0`（中文估时长用）。
- [ ] 写失败测试（test_cost_service）：数字人 provider `estimate_cost({"duration_sec": 10})` == `10*0.5`；视频 provider `estimate_cost({"duration_sec": 5})` == `5*1.0`。
- [ ] 跑测试确认失败。
- [ ] 实现两个 placeholder 的 `estimate_cost`：`return request.get("duration_sec", 0) * settings.<rate>`。
- [ ] 跑测试确认通过。
- [ ] 提交：`feat(providers): 数字人/生成式占位 Provider 增加费率估价`

### Task 6：CostService（估算 + 配额 + 汇总）
**Files:** Create `backend/app/services/cost_service.py`、`backend/app/schemas/cost.py`；Test `backend/tests/test_cost_service.py`

- [ ] 写失败测试：
  - `estimate_ir_cost(ir)`：构造含 1 个 digital_human（旁白 40 字→10s）、1 个 generative（gen_prompt，按固定 5s）、若干 slide 的 IR；断言 total>0 且 breakdown 含对应类型；slide/formula 计 0。
  - `check_quota`：播种 Project + 一条 `actual_cost` 已花费的 Task；估算超 `MAX_COST_PER_TASK` 抛 `CostLimitException`；已花费+估算超 `MAX_COST_PER_PROJECT` 抛；正常不抛。
  - `project_cost_summary`：返回任务计数、累计 actual、存储用量（用 Resource）。
- [ ] 跑测试确认失败。
- [ ] 实现 `cost_service.py`：
  - `Segment 估时`：digital_human 时长≈`len(narration)/TTS_CHARS_PER_SEC`；generative 固定 `config.get("clip_seconds",5)`。
  - `estimate_ir_cost(ir, config=None) -> CostEstimate`：展平（复用 composition_service._flatten 或本地展平）→ 按 scene_type 调对应 provider.estimate_cost → 汇总 total + breakdown(dict[type]->cost)。
  - `async check_quota(db, project_id, estimated)`：`spent = select(func.coalesce(func.sum(Task.actual_cost),0)).where(Task.project_id==pid)`；超额抛 `CostLimitException`。
  - `async project_cost_summary(db, project_id) -> CostSummary`、`async dashboard_stats(db) -> DashboardStats`：用 `func.count/sum`、`Resource.file_size` 聚合。
  - schemas/cost.py：`CostEstimate{total: float, breakdown: dict[str,float], currency:"CNY"}`、`CostSummary`、`DashboardStats`。
- [ ] 跑测试确认通过。
- [ ] 提交：`feat(cost): 新增 CostService（IR 成本估算 / 配额护栏 / 汇总）`

### Task 7：监控与成本 API
**Files:** Create `backend/app/api/v1/monitoring.py`；Modify `backend/app/api/v1/__init__.py`；Test `backend/tests/test_monitoring_api.py`

- [ ] 写失败测试（用 conftest `client`）：建项目+上传 .md 跑到 reviewing 后：`GET /api/v1/projects/{id}/cost-estimate` 200 且含 total/breakdown；`GET /api/v1/projects/{id}/cost` 200；`GET /api/v1/monitoring/dashboard` 200 含任务计数。
- [ ] 跑测试确认失败。
- [ ] 实现 `monitoring.py`（router 无前缀，全路径显式）：
  - `GET /projects/{project_id}/cost-estimate`：`load_ir` → `estimate_ir_cost` → 返回 CostEstimate（无 IR→404）。
  - `GET /projects/{project_id}/cost`：`project_cost_summary`。
  - `GET /monitoring/dashboard`：`dashboard_stats`。
  - `__init__.py` `include_router(monitoring_router)`。
- [ ] 跑测试确认通过。
- [ ] 提交：`feat(api): 成本预估 / 项目成本 / 监控面板端点`

### Task 8：approve_script 接入配额护栏
**Files:** Modify `backend/app/api/v1/scripts.py`；Test `backend/tests/test_upload_api.py`

- [ ] 写失败测试：把 `settings.MAX_COST_PER_PROJECT` 调到极小并让 IR 估算>它（含 digital_human），`POST approve` 返回 429。正常情况下（free stack 估算 0）仍 200 并返回 task_id。
- [ ] 跑测试确认失败。
- [ ] 实现 approve_script：`est = estimate_ir_cost(ir)` → `await check_quota(db, str(project_id), est.total)`（CostLimitException 由全局处理器→429）→ 建 Task 时 `estimated_cost=est.total` → 启动合成。
- [ ] `composition_service.compose` 收尾设 `task.actual_cost = Σ subtask.cost`。
- [ ] 跑测试确认通过。
- [ ] 提交：`feat(cost): approve 生成前做配额护栏并记录成本`

---

## 特性 ③ SKIP_REVIEW 一键全自动

### Task 9：SKIP_REVIEW 开关
**Files:** Modify `backend/app/config.py`、`backend/app/api/v1/upload.py`；Test `backend/tests/test_skip_review.py`

- [ ] config 增 `SKIP_REVIEW: bool = False`。
- [ ] 写失败测试：monkeypatch `app.services.composition_service.CompositionService.compose` 为 AsyncMock 探针 + monkeypatch settings.SKIP_REVIEW；驱动 `_run_parse_in_background`（或上传端点），`SKIP_REVIEW=True` 时探针被调用一次、False 时 0 次。（解析/编排用最小 .md + 无 LLM key 本地降级，避免网络。）
- [ ] 跑测试确认失败。
- [ ] 实现 `_run_parse_in_background`：orchestrate 后若 `settings.SKIP_REVIEW`：`ir=load_ir`；`est=estimate_ir_cost(ir)`；`try check_quota` 失败则置 task failed 返回；否则 `task.estimated_cost=est.total` 并 `CompositionService().compose(...)`。
- [ ] 跑测试确认通过。
- [ ] 提交：`feat(pipeline): SKIP_REVIEW 支持上传后一键全自动出片`

---

## 收尾验证
- [ ] 全量 `pytest tests/ -q`（含 ffmpeg PATH）全绿。
- [ ] `ruff check .` + `black --check .` 全绿。
- [ ] 端到端：`SKIP_REVIEW=True` 上传一个 PDF → 自动出片且用真页图；`GET /monitoring/dashboard`、`/projects/{id}/cost` 返回合理数据。
- [ ] 更新 README/AGENTS 的命令与配置说明（如新增 env 项）。

## Self-Review 结论
- 覆盖 spec 全部三特性与监控端点；无占位；类型/签名（`background_path`、`estimate_ir_cost`、`check_quota`、`CostEstimate`）跨任务一致。
- 顺序：①(1-4) → ②(5-8) → ③(9)，②先于③（③复用 estimate/check_quota）。
