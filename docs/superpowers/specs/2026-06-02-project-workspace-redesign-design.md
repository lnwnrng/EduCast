# 项目工作台重构 — 设计

> 日期：2026-06-02 ｜ 状态：已与用户确认方向，待评审后转实施计划
> 目标：把"上传→脚本→生成→预览→改了再来"这条**迭代闭环**做成一等公民，消除当前
> 一次性线性流水线带来的逻辑断点。

## 诊断（当前逻辑断点）

1. 没有「重新生成」入口——`completed` 项目的生成页只剩"查看结果"，是死胡同。
2. 改了脚本后成片不知道自己过期了（项目仍显示 completed，无"待重生成"提示）。
3. 「AI 重新编排」会覆盖手动修改，且把 completed 拉回 reviewing（footgun）。
4. 生成配置表单（音色/数字人/模板）`approve` 不接收，填了完全不生效。
5. 缺"我在第几步 / 下一步点什么"的统一视图，主流程不可见。
6. 重新生成版本语义混乱：未改脚本重生成会覆盖同名 mp4 并重复插入资源记录。
7. 各页状态文案不一致。

## 已确认决策

1. **全量重构**：新增「项目工作台」详情页作为唯一枢纽。
2. **保留多版本历史**：每次生成 = 一个独立 generation 版本，可看历史/切播/下载。
3. **配置项**：TTS 音色打通生效；数字人/模板禁用并标「待模块 4/5」。

## 目标流程（一句话）

上传 → 在工作台审核/改脚本 → 一键生成（带成本预估、选音色）→ 预览 →
不满意就回去改脚本，工作台标「已过期」→ 重新生成（产出新版本，可对比/下载）。

---

## 后端改动

### 1. 生成版本号（清理覆盖与重复资源）— `services/composition_service.py`
- 在 compose 开始时计算 `gen_version = 该项目现有 video 资源数 + 1`（查询 Resource）。
- 产物按 generation 命名：`output/gen{N}.mp4` / `.srt` / `.vtt` / `_cover.png`、`export/gen{N}.zip`。
- 入库 `Resource.version = N`，`metadata_json` 记 `{ir_version, task_id}`。
- 效果：每次生成都是独立版本，不再覆盖同名文件、不再重复插入。

### 2. 配置透传（TTS 音色生效）— `api/v1/scripts.py` + `composition_service.py`
- `approve_script` 接收可选 body `{ "config": { "tts_voice"?: str } }`，存入 `Task.config_json`。
- CompositionService 读取 `config.tts_voice`，逐镜 `EdgeTTSProvider.synthesize(text, path, voice=...)`（provider 已支持 voice 参数）。

### 3. 工作台聚合端点 — `api/v1/monitoring.py`（或新 `projects` 子路由）
- `GET /projects/{id}/workspace` 返回工作台一次渲染所需数据：
  ```
  { project, latest_task, latest_ir_version,
    videos: [{version, ir_version, resource_id, created_at}],
    is_stale, cost_estimate }
  ```
- `is_stale = latest_ir_version > 最新视频的 ir_version`（脚本改过、成片过期）。
- 复用 `parser_service.load_ir`、`ResourceService.list_resources`、`cost_service.estimate_ir_cost`。

### 4. 重新生成
- 复用 `approve_script`（产出新 gen 版本）；无需新端点。

### 5. 测试
- gen_version 递增与命名；重复生成不产生重复同名资源；`config.tts_voice` 透传到 synthesize；`/workspace` 聚合 + `is_stale` 计算；approve 重新生成产出 gen2。

---

## 前端改动

### 1. 新页 `pages/Workspace`（路由 `/projects/:id`）
状态驱动的单一主操作 + Steps 进度条（解析 → 脚本审核 → 生成 → 预览）：
- **reviewing**：成本预估卡 + TTS 音色下拉 + 主按钮「开始生成」+ 次「去编辑脚本」。
- **parsing/scripting/generating/composing**：进度轮询（getTask）。
- **completed**：最新版 `<video>` 播放 + 「重新生成」+「回到脚本修改」+ 版本历史列表（gen1/gen2…，标注源自脚本 v? + 时间，可切播/下载该版 zip）+ 过期时显示「脚本已修改，建议重新生成」。
- **failed**：错误信息 + 「重试」。
- 数据来自 `GET /projects/{id}/workspace` + 轮询。

### 2. 路由 / 枢纽收编
- 项目表格行「进入工作台」为主操作（保留删除）。
- 侧边栏精简：视频生成折入工作台；预览作为工作台内嵌（保留 `/projects/:id/preview` 直链）。

### 3. 配置项
- 生成区只留 TTS 音色（生效）；数字人/模板 `disabled` 并标「待模块 4/5」。

### 4. 统一状态机文案 — `utils/status.ts`
- 抽出共享 `statusConfig`（color + label），Dashboard/Projects/Workspace/Monitoring 统一引用。

### 5. 防 footgun
- ScriptEditor「AI 重新编排」加二次确认：提示会用 LLM 重写讲稿、覆盖手动修改。

### 6. 验证
- tsc + eslint + `npm run build` 全绿。

---

## 端到端验收

上传 PDF → 工作台审核（看到成本预估、选音色）→ 生成 → 预览播放 → 回脚本改一句 →
工作台显示「已过期」→ 重新生成 → 历史出现 gen2 → 可切换播放/下载 gen1/gen2。

## 不在本轮范围

- 数字人/生成式真实 API（模块 4/5）；版本「对比」视图（仅做切播/下载，不做并排 diff）；
  题库独立页（模块六）。
