"""LLM 脚本编排器 — 将 IR 草稿就地增强为可生产 IR。

使用 GLM-4.7-Flash 完成（详见需求文档 5.2）:
- 讲稿口语化
- 画面类型重判（slide / formula_animation / digital_human / generative_clip）
- 生成式片段提示词与公式推导步骤
- 知识点标签与随堂练习题
- 课程元信息推断（学科 / 年级 / 受众）

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
    """LLM 脚本编排器。"""

    def __init__(self, llm_provider: ZhipuLLMProvider | None) -> None:
        self._llm = llm_provider

    async def enhance_ir(
        self,
        draft_ir: CourseIR,
        *,
        progress_cb: ProgressCallback | None = None,
    ) -> CourseIR:
        """将 IR 草稿就地增强为完整可生产 IR。

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
            "开始 LLM 脚本编排: %s — %d 章节, %d 知识点",
            ir.title,
            len(ir.chapters),
            total_kps,
        )

        # 1. 课程元信息推断
        await self._infer_course_metadata(ir)

        # 2. 逐知识点增强
        done = 0
        for chapter in ir.chapters:
            for kp in chapter.knowledge_points:
                try:
                    await self._enhance_kp(ir, chapter, kp)
                except Exception as exc:  # noqa: BLE001 — 单点失败不阻断整体
                    logger.warning("知识点 '%s' 编排失败，保留原文: %s", kp.title, exc)
                done += 1
                if progress_cb:
                    await progress_cb(done, total_kps)

        logger.info("LLM 脚本编排完成: %s", ir.title)
        return ir

    # ── 课程元信息 ───────────────────────────────────────────

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

    # ── 知识点增强 ───────────────────────────────────────────

    async def _enhance_kp(
        self,
        ir: CourseIR,
        chapter: ChapterIR,
        kp: KnowledgePointIR,
    ) -> None:
        """对单个知识点调用 LLM 并把结果合并回 IR。"""
        if not kp.scenes:
            return

        messages = self._build_kp_messages(ir, chapter, kp)
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
    ) -> list[dict[str, str]]:
        """构造单个知识点的编排提示词。"""
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

        system = (
            "你是资深的高校教学视频编导与讲稿撰写专家。你的任务是把课件解析出的"
            "原始文字，改写成适合教师口播的教学讲稿，并规划每个分镜的画面类型。\n"
            f"课程学科：{subject}；目标受众：{audience}；"
            f"讲解风格：{tpl.prompt_style}。\n"
            "要求：\n"
            "1. narration_text：把原始文字扩写为自然、口语化、可朗读的讲解稿，"
            "补充必要的过渡与解释，避免照搬罗列；每个分镜 60~150 字为宜。\n"
            "2. 字幕将由系统从 narration_text 自动切句生成，不要另写摘要字幕。\n"
            "3. scene_type：从 slide(课件页) / formula_animation(公式推导动画) / "
            "digital_human(数字人讲解) / generative_clip(生成式概念片段) 中选择最"
            "合适的；纯公式推导选 formula_animation，引入/小结类选 digital_human，"
            "需要情景画面的选 generative_clip，其余默认 slide。\n"
            f"本模板偏好：{tpl.scene_type_hint}。\n"
            "4. 当 scene_type=formula_animation，在 latex_steps 给出逐步推导的 "
            "LaTeX 字符串数组；当 scene_type=generative_clip，在 gen_prompt 给出一句"
            "中文画面提示词。其它情况这两个字段留空。\n"
            "5. 必须严格输出 JSON，且 scenes 的 order 与输入一一对应、不增不减。"
        )

        user = (
            f"知识点标题：{kp.title}\n"
            f"知识点要点：\n{key_points_block}\n\n"
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
            '"narration_text": "口语化讲稿", '
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


def _collapse_whitespace(text: str) -> str:
    """把连续空白/换行折叠为单空格。"""
    return re.sub(r"\s+", " ", (text or "").strip())


def _as_str_list(value: Any) -> list[str]:
    """把任意值规整为非空字符串列表。"""
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]
