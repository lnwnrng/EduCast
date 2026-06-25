"""LLM 脚本编排器 — 多智能体管道将 IR 草稿就地增强为可生产 IR。

使用 GLM-4.7-Flash 完成（详见需求文档 5.2）:
- 讲稿口语化
- 画面类型重判（slide / formula_animation / digital_human / generative_clip）
- 生成式片段提示词与公式推导步骤
- 知识点标签与随堂练习题
- 课程元信息推断（学科 / 年级 / 受众）

三阶段多智能体管道:
- **Stage 1 — Outline Agent**: 全课程教学大纲 + 叙事弧线 + 各知识点教学策略
- **Stage 2 — Scene Agent**: 逐知识点精写讲稿（继承大纲上下文 + SSML 标注）
- **Stage 3 — Review Agent**: 全课程质量审校 + 衔接优化

设计原则:
- **原地增强**: 保留解析得到的「每页一个分镜」骨架及 scene_id / slide_ref /
  source_page / image_refs，LLM 只覆盖文本与类型字段。
- **逐知识点处理**: 粒度小、稳、可报进度；免费档不并发以免触发限流。
- **降级**: 单个知识点失败保留原文继续；无 LLM Provider 时做本地轻量规整。
"""

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from app.ir.schema import (
    ChapterIR,
    CourseIR,
    KnowledgePointIR,
    QuizSeed,
    SceneIR,
    SceneType,
)
from app.providers.llm.zhipu import ZhipuLLMProvider
from app.utils.json_parse import extract_json

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], Awaitable[None]]

# 单个分镜原始文字截断长度，避免超长输入
_MAX_SCENE_CHARS = 1500
# 文件名前缀（解析阶段用 8 位 hex 防冲突），清理课程标题时去除
_FILENAME_PREFIX_RE = re.compile(r"^[0-9a-f]{8}_")
_VALID_SCENE_TYPES = {t.value for t in SceneType}


class ScriptWriter:
    """LLM 脚本编排器 — 三阶段多智能体管道。"""

    def __init__(self, llm_provider: ZhipuLLMProvider | None) -> None:
        self._llm = llm_provider

    async def enhance_ir(
        self,
        draft_ir: CourseIR,
        *,
        progress_cb: ProgressCallback | None = None,
    ) -> CourseIR:
        """将 IR 草稿就地增强为完整可生产 IR。

        三阶段管道:
          Stage 1 (Outline Agent)  — 生成教学大纲与叙事弧线
          Stage 2 (Scene Agent)    — 逐知识点精写讲稿 + SSML 标注
          Stage 3 (Review Agent)   — 全课程质量审校

        Args:
            draft_ir: 解析阶段产出的草稿 IR。
            progress_cb: 可选的异步进度回调 (已完成知识点数, 总知识点数)。

        Returns:
            增强后的 CourseIR（在副本上修改，不改动入参）。
        """
        ir = draft_ir.model_copy(deep=True)

        # 课程标题始终先做本地清理（去文件名前缀）
        ir.title = _clean_title(ir.title)

        total_kps = sum(len(ch.knowledge_points) for ch in ir.chapters)

        if self._llm is None:
            logger.warning(
                "未配置 LLM Provider，脚本编排降级为本地轻量规整: %s",
                ir.title,
            )
            _local_normalize(ir)
            if progress_cb:
                await progress_cb(total_kps, total_kps)
            return ir

        logger.info(
            "开始 LLM 脚本编排（三阶段管道）: %s — %d 章节, %d 知识点",
            ir.title,
            len(ir.chapters),
            total_kps,
        )

        # Stage 0: 课程元信息推断
        await self._infer_course_metadata(ir)

        # Stage 1: Outline Agent — 教学大纲 + 叙事弧线
        outline = await self._generate_teaching_outline(ir)
        ir.teaching_outline = outline

        # Stage 2: Scene Agent — 逐知识点增强（注入大纲上下文）
        done = 0
        for ci, chapter in enumerate(ir.chapters):
            for ki, kp in enumerate(chapter.knowledge_points):
                try:
                    # 构造上下文：大纲策略 + 前后知识点
                    ctx = _build_kp_context(ir, outline, ci, ki)
                    await self._enhance_kp(ir, chapter, kp, ctx)
                except Exception as exc:  # noqa: BLE001 — 单点失败不阻断整体
                    logger.warning("知识点 '%s' 编排失败，保留原文: %s", kp.title, exc)
                done += 1
                if progress_cb:
                    await progress_cb(done, total_kps)

        # Stage 3: Review Agent — 全课程质量审校
        await self._review_full_script(ir)

        logger.info("LLM 脚本编排完成（三阶段管道）: %s", ir.title)
        return ir

    # ── Stage 0: 课程元信息 ──────────────────────────────────

    async def _infer_course_metadata(self, ir: CourseIR) -> None:
        """调用 LLM 推断课程标题/学科/年级/受众，回填空缺字段。"""
        outline = _build_outline(ir)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是高校教学视频的策划专家。请根据课程提纲推断课程的"
                    "元信息，并严格以 JSON 格式输出。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"课程当前标题：{ir.title or '（未知）'}\n\n"
                    f"课程提纲：\n{outline}\n\n"
                    "请严格输出如下 JSON（不要输出多余文字）：\n"
                    "{\n"
                    '  "title": "更规范的课程标题",\n'
                    '  "subject": "学科，如 高等数学 / 大学物理 / 数据结构",\n'
                    '  "grade": "适用年级，如 大学一年级",\n'
                    '  "target_audience": "目标受众一句话描述"\n'
                    "}"
                ),
            },
        ]
        try:
            result = await self._llm.chat(
                messages,
                temperature=0.3,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            data = extract_json(result.content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("课程元信息推断失败: %s", exc)
            return

        if not data:
            logger.warning("课程元信息 JSON 解析失败")
            return

        if data.get("title"):
            ir.title = str(data["title"]).strip()
        if not ir.subject and data.get("subject"):
            ir.subject = str(data["subject"]).strip()
        if not ir.grade and data.get("grade"):
            ir.grade = str(data["grade"]).strip()
        if not ir.target_audience and data.get("target_audience"):
            ir.target_audience = str(data["target_audience"]).strip()

    # ── Stage 1: Outline Agent — 教学大纲 ──────────────────

    async def _generate_teaching_outline(self, ir: CourseIR) -> dict:
        """生成全课程教学大纲：叙事弧线、各知识点策略、知识点间衔接。"""
        from app.pipeline.templates import get_template

        outline_text = _build_outline(ir)
        tpl = get_template(ir.template or "micro_lecture")
        subject = ir.subject or "通用学科"
        audience = ir.target_audience or "高校学生"

        messages = [
            {
                "role": "system",
                "content": (
                    "你是资深的高校教学设计专家和课程编导。你的任务是为一门完整"
                    "课程设计教学大纲和叙事弧线。\n\n"
                    "你需要分析课程提纲，输出一份详细的教学设计方案：\n"
                    "1. **教学叙事弧线**：整门课程的起承转合——如何引入悬念、"
                    "铺垫概念、推导核心、应用拓展、总结升华\n"
                    "2. **各知识点教学策略**：每个知识点采用什么教学法（直接讲授 "
                    "/ 问题驱动 / 类比说明 / 案例分析 / 苏格拉底式追问）\n"
                    "3. **知识点间的衔接语**：前一个知识点到下一个知识点的自然过渡\n"
                    "4. **关键画面指令**：哪些知识点适合概念动画、教师出镜、"
                    "公式推导动画\n"
                    "5. **节奏规划**：哪些部分需要放慢讲（难点），哪些可以加速"
                    "（回顾），哪些需要停顿让学生思考\n\n"
                    f"课程学科：{subject}\n"
                    f"目标受众：{audience}\n"
                    f"课程模板：{tpl.display_name}（{tpl.description}）\n"
                    f"讲解风格：{tpl.prompt_style}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"课程标题：{ir.title}\n\n"
                    f"课程提纲：\n{outline_text}\n\n"
                    "请严格输出如下 JSON（不要输出多余文字）：\n"
                    "{\n"
                    '  "narrative_arc": "整门课程的叙事弧线描述（一段话）",\n'
                    '  "opening_hook": "课程开场引入悬念/问题的设计",\n'
                    '  "closing_summary": "课程总结升华的设计",\n'
                    '  "kp_strategies": [\n'
                    "    {\n"
                    '      "kp_title": "知识点标题",\n'
                    '      "teaching_method": "教学法名称",\n'
                    '      "pacing": "slow|normal|fast",\n'
                    '      "transition_in": "从前一知识点过渡的衔接语",\n'
                    '      "visual_hint": "slide|formula_animation|digital_human|'
                    'generative_clip",\n'
                    '      "pause_points": "需要停顿让学生思考的地方描述"\n'
                    "    }\n"
                    "  ]\n"
                    "}"
                ),
            },
        ]
        try:
            result = await self._llm.chat(
                messages,
                temperature=0.4,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            data = extract_json(result.content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("教学大纲生成失败，继续无大纲模式: %s", exc)
            return {}

        if not data:
            logger.warning("教学大纲 JSON 解析失败")
            return {}

        logger.info(
            "Outline Agent 完成: 叙事弧线 + %d 条知识点策略",
            len(data.get("kp_strategies", [])),
        )
        return data

    # ── Stage 2: Scene Agent — 知识点增强 ──────────────────

    async def _enhance_kp(
        self,
        ir: CourseIR,
        chapter: ChapterIR,
        kp: KnowledgePointIR,
        context: dict,
    ) -> None:
        """对单个知识点调用 LLM 并把结果合并回 IR。"""
        if not kp.scenes:
            return

        messages = self._build_kp_messages(ir, chapter, kp, context)
        result = await self._llm.chat(
            messages,
            temperature=0.6,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        data = extract_json(result.content)
        if not data:
            raise ValueError("知识点 JSON 解析失败")

        self._merge_kp(kp, data)

    def _build_kp_messages(
        self,
        ir: CourseIR,
        chapter: ChapterIR,
        kp: KnowledgePointIR,
        context: dict,
    ) -> list[dict[str, str]]:
        """构造单个知识点的编排提示词（注入 Outline Agent 上下文）。"""
        from app.pipeline.templates import get_template

        subject = ir.subject or "通用学科"
        audience = ir.target_audience or "高校学生"
        tpl = get_template(ir.template or "micro_lecture")

        scene_lines: list[str] = []
        for scene in kp.scenes:
            raw = (scene.narration_text or "").strip()
            if len(raw) > _MAX_SCENE_CHARS:
                raw = raw[:_MAX_SCENE_CHARS] + "…"
            scene_lines.append(
                f"- 分镜 order={scene.order}（来源第 "
                f"{scene.source_page or '?'} 页）原始文字：\n{raw or '（空）'}"
            )
        scenes_block = "\n".join(scene_lines)
        key_points_block = (
            "\n".join(f"- {p}" for p in kp.key_points) if kp.key_points else "（无）"
        )

        # 从 Outline Agent 注入上下文
        strategy = context.get("strategy", "")
        transition_in = context.get("transition_in", "")
        next_kp_title = context.get("next_kp_title", "")
        pacing = context.get("pacing", "normal")
        pause_points = context.get("pause_points", "")

        strategy_block = ""
        if strategy or transition_in:
            strategy_block = (
                "\n\n【教学设计师为本知识点规划的策略】\n"
                f"教学法：{strategy}\n"
                f"节奏：{pacing}\n"
                f"与前一知识点的衔接：{transition_in or '（首个知识点，无需衔接）'}\n"
                f"后续知识点：{next_kp_title or '（最后一个知识点）'}\n"
                f"建议停顿点：{pause_points or '（无特别指定）'}"
            )

        system = (
            "你是资深的高校教学视频编导与讲稿撰写专家。你的任务是把课件解析出的"
            "原始文字，改写成适合教师口播的教学讲稿，并规划每个分镜的画面类型。\n"
            f"课程学科：{subject}；目标受众：{audience}；"
            f"讲解风格：{tpl.prompt_style}。\n"
            "要求：\n"
            "1. narration_text：把原始文字扩写为自然、口语化、可朗读的讲解稿，"
            "补充必要的过渡与解释，避免照搬罗列；每个分镜 80~250 字为宜，"
            "复杂推导允许 300 字。\n"
            "2. 字幕将由系统从 narration_text 自动切句生成，不要另写摘要字幕。\n"
            "3. scene_type：从 slide(课件页) / formula_animation(公式推导动画) / "
            "digital_human(数字人讲解) / generative_clip(生成式概念片段) 中选择最"
            "合适的；纯公式推导选 formula_animation，引入/小结类选 digital_human，"
            "需要情景画面的选 generative_clip，其余默认 slide。\n"
            f"本模板偏好：{tpl.scene_type_hint}。\n"
            "4. 当 scene_type=formula_animation，在 latex_steps 给出逐步推导的 "
            "LaTeX 字符串数组；当 scene_type=generative_clip，在 gen_prompt 给出一句"
            "中文画面提示词。其它情况这两个字段留空。\n"
            "5. 必须严格输出 JSON，且 scenes 的 order 与输入一一对应、不增不减。\n"
            "6. **SSML 语音标注**：在讲稿中插入语音控制标记以提升配音韵律——\n"
            "   - 在需要学生思考或段落转换处插入 [PAUSE:0.5]（数字为秒数）\n"
            "   - 在重要概念/术语首次出现时用 [EMPHASIS]重要内容[/EMPHASIS] 包裹\n"
            "   - 在复杂公式解释等需要放慢的地方用 [SLOW]缓讲内容[/SLOW] 包裹\n"
            "   每个分镜至少包含 1 个 [PAUSE]。\n"
            "7. **教学策略感知**：你已获得教学设计师为本知识点规划的教学策略，"
            "请在讲稿中自然融入。注意衔接语要自然不生硬。\n"
            "8. **视觉配合**：当 scene_type=slide 时，讲稿中要有对画面的引导词"
            "（如「请看屏幕上的…」「如图所示…」「我们来看这个公式…」），"
            "让观众知道看哪里。\n"
            "9. **过渡句**：除首个分镜外，必须包含与上一个分镜的自然衔接。"
        )

        user = (
            f"知识点标题：{kp.title}\n"
            f"知识点要点：\n{key_points_block}\n"
            f"{strategy_block}\n\n"
            f"该知识点包含以下分镜：\n{scenes_block}\n\n"
            "请严格输出如下 JSON（不要输出多余文字或解释）：\n"
            "{\n"
            '  "tags": ["该知识点的2~4个关键词标签"],\n'
            '  "quiz_seeds": [\n'
            '    {"question": "针对该知识点的练习题", '
            '"question_type": "mcq|fill|short|calc", '
            '"answer": "答案", "explanation": "解析"}\n'
            "  ],\n"
            '  "scenes": [\n'
            '    {"order": 1, "scene_type": "slide", '
            '"narration_text": "含[PAUSE][EMPHASIS]等标记的口语化讲稿", '
            '"gen_prompt": "", "latex_steps": []}\n'
            "  ]\n"
            "}"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _merge_kp(self, kp: KnowledgePointIR, data: dict[str, Any]) -> None:
        """把 LLM 返回的 JSON 合并回知识点，保留结构性字段。"""
        # 知识点级：标签与练习题
        tags = _as_str_list(data.get("tags"))
        if tags:
            kp.tags = tags

        quiz_seeds = data.get("quiz_seeds")
        if isinstance(quiz_seeds, list):
            parsed_quiz: list[QuizSeed] = []
            for q in quiz_seeds:
                if not isinstance(q, dict) or not q.get("question"):
                    continue
                parsed_quiz.append(
                    QuizSeed(
                        question=str(q.get("question", "")).strip(),
                        question_type=str(q.get("question_type") or "mcq"),
                        answer=str(q.get("answer") or "").strip(),
                        explanation=str(q.get("explanation") or "").strip(),
                    )
                )
            if parsed_quiz:
                kp.quiz_seeds = parsed_quiz

        # 分镜级：按 order 合并，仅覆盖文本与类型字段
        scene_map: dict[int, dict[str, Any]] = {}
        for s in data.get("scenes") or []:
            if isinstance(s, dict) and isinstance(s.get("order"), int):
                scene_map[s["order"]] = s

        for scene in kp.scenes:
            s = scene_map.get(scene.order)
            if not s:
                continue
            _apply_scene(scene, s, kp_tags=tags)

    # ── Stage 3: Review Agent — 全课程审校 ─────────────────

    async def _review_full_script(self, ir: CourseIR) -> None:
        """全课程质量审校：检查衔接、重复、口语化、深度、节奏。"""
        # 收集全部分镜讲稿（按顺序）
        all_scenes: list[tuple[int, int, int, SceneIR]] = []
        for ci, ch in enumerate(ir.chapters):
            for ki, kp in enumerate(ch.knowledge_points):
                for scene in kp.scenes:
                    all_scenes.append((ci, ki, scene.order, scene))

        if len(all_scenes) < 3:
            # 太短的课程不需要全局审校
            return

        # 构造审校输入（限制长度，取前 40 个分镜）
        review_scenes = all_scenes[:40]
        scene_summaries: list[str] = []
        for ci, ki, order, scene in review_scenes:
            text = (scene.narration_text or "").strip()
            if len(text) > 200:
                text = text[:200] + "…"
            scene_summaries.append(
                f"[章{ci + 1}-知{ki + 1}-镜{order}] {text}"
            )
        script_block = "\n".join(scene_summaries)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是高校教学视频的审校编辑。请逐一检查以下课程的完整讲稿，"
                    "找出并修正以下问题：\n\n"
                    "1. **衔接断裂**：前后分镜之间缺少过渡、突然跳转\n"
                    "2. **重复冗余**：相同概念被多次重复解释\n"
                    "3. **口语化不足**：仍然像 PPT 要点罗列而非教师口播\n"
                    "4. **深度不够**：重要概念一笔带过、没有展开解释\n"
                    "5. **节奏单调**：连续多个分镜都是同一节奏\n"
                    "6. **SSML 标注不足**：确保每个分镜至少有 1 个 [PAUSE]，"
                    "关键术语有 [EMPHASIS]\n\n"
                    "只输出需要修改的分镜。不需要修改的不要输出。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"课程标题：{ir.title}\n"
                    f"学科：{ir.subject or '通用'}\n\n"
                    f"完整讲稿（按分镜顺序）：\n{script_block}\n\n"
                    "请严格输出如下 JSON（不要输出多余文字）：\n"
                    "{\n"
                    '  "corrections": [\n'
                    "    {\n"
                    '      "chapter_index": 0,\n'
                    '      "kp_index": 0,\n'
                    '      "scene_order": 1,\n'
                    '      "narration_text": "修正后的完整讲稿（含SSML标记）",\n'
                    '      "reason": "修改原因简述"\n'
                    "    }\n"
                    "  ]\n"
                    "}"
                ),
            },
        ]
        try:
            result = await self._llm.chat(
                messages,
                temperature=0.4,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            data = extract_json(result.content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Review Agent 审校失败，保留原稿: %s", exc)
            return

        if not data or not data.get("corrections"):
            logger.info("Review Agent: 无需修正")
            return

        # 应用修正
        corrections = data.get("corrections", [])
        applied = 0
        for c in corrections:
            if not isinstance(c, dict):
                continue
            ci = c.get("chapter_index")
            ki = c.get("kp_index")
            order = c.get("scene_order")
            new_text = (c.get("narration_text") or "").strip()
            if ci is None or ki is None or order is None or not new_text:
                continue
            try:
                scene = ir.chapters[ci].knowledge_points[ki].scenes[order - 1]
                if scene.order == order:
                    scene.narration_text = new_text
                    scene.subtitle_text = new_text
                    applied += 1
                    logger.debug(
                        "Review Agent 修正: 章%d-知%d-镜%d — %s",
                        ci + 1,
                        ki + 1,
                        order,
                        c.get("reason", ""),
                    )
            except (IndexError, AttributeError):
                continue

        logger.info("Review Agent 完成: 修正了 %d 个分镜", applied)


# ── 合并与本地降级辅助函数 ───────────────────────────────────


def _apply_scene(
    scene: SceneIR,
    data: dict[str, Any],
    *,
    kp_tags: list[str],
) -> None:
    """把单条 LLM 分镜结果应用到 SceneIR（保留结构性字段）。"""
    narration = str(data.get("narration_text") or "").strip()
    if narration:
        scene.narration_text = narration

    if narration:
        scene.subtitle_text = narration

    scene_type = data.get("scene_type")
    if scene_type in _VALID_SCENE_TYPES:
        scene.scene_type = SceneType(scene_type)

    if scene.scene_type == SceneType.GENERATIVE_CLIP:
        gen_prompt = str(data.get("gen_prompt") or "").strip()
        if gen_prompt:
            scene.visual_spec.gen_prompt = gen_prompt

    if scene.scene_type == SceneType.FORMULA_ANIMATION:
        latex_steps = _as_str_list(data.get("latex_steps"))
        if latex_steps:
            scene.visual_spec.latex_steps = latex_steps

    if kp_tags:
        scene.kp_tags = list(kp_tags)


def _local_normalize(ir: CourseIR) -> None:
    """无 LLM 时的本地轻量规整：折叠空白、同步兼容字幕字段。"""
    for chapter in ir.chapters:
        for kp in chapter.knowledge_points:
            for scene in kp.scenes:
                text = _collapse_whitespace(scene.narration_text)
                scene.narration_text = text
                scene.subtitle_text = text


def _clean_title(title: str) -> str:
    """清理课程标题：去掉上传文件名的 8 位 hex 前缀。"""
    cleaned = _FILENAME_PREFIX_RE.sub("", (title or "").strip())
    return cleaned or title


def _build_outline(ir: CourseIR, max_kps: int = 30) -> str:
    """构造课程提纲文本（章节标题 + 知识点标题）。"""
    lines: list[str] = []
    count = 0
    for ch in ir.chapters:
        lines.append(f"# {ch.title}")
        for kp in ch.knowledge_points:
            lines.append(f"  - {kp.title}")
            count += 1
            if count >= max_kps:
                lines.append("  - …")
                return "\n".join(lines)
    return "\n".join(lines)


def _build_kp_context(
    ir: CourseIR,
    outline: dict,
    chapter_index: int,
    kp_index: int,
) -> dict:
    """从 Outline Agent 产出中提取当前知识点的上下文。"""
    chapter = ir.chapters[chapter_index]
    kp = chapter.knowledge_points[kp_index]
    kp_strategies = outline.get("kp_strategies", [])

    # 按标题匹配策略
    strategy_entry: dict = {}
    for s in kp_strategies:
        if isinstance(s, dict) and s.get("kp_title") == kp.title:
            strategy_entry = s
            break

    # 下一个知识点标题（用于铺垫）
    next_kp_title = ""
    if kp_index + 1 < len(chapter.knowledge_points):
        next_kp_title = chapter.knowledge_points[kp_index + 1].title
    elif chapter_index + 1 < len(ir.chapters):
        next_ch = ir.chapters[chapter_index + 1]
        if next_ch.knowledge_points:
            next_kp_title = next_ch.knowledge_points[0].title

    return {
        "strategy": strategy_entry.get("teaching_method", ""),
        "pacing": strategy_entry.get("pacing", "normal"),
        "transition_in": strategy_entry.get("transition_in", ""),
        "pause_points": strategy_entry.get("pause_points", ""),
        "visual_hint": strategy_entry.get("visual_hint", ""),
        "next_kp_title": next_kp_title,
        "opening_hook": outline.get("opening_hook", ""),
        "closing_summary": outline.get("closing_summary", ""),
    }


def _collapse_whitespace(text: str) -> str:
    """把连续空白/换行折叠为单空格。"""
    return re.sub(r"\s+", " ", (text or "").strip())


def _as_str_list(value: Any) -> list[str]:
    """把任意值规整为非空字符串列表。"""
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]
