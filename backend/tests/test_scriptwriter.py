"""ScriptWriter（LLM 脚本编排器）测试。

使用注入的 FakeLLM（不发起真实 API 调用）验证编排合并、降级与本地兜底。
"""

import json

import pytest

from app.ir.schema import (
    ChapterIR,
    CourseIR,
    KnowledgePointIR,
    SceneIR,
    SceneType,
    VisualSpec,
)
from app.pipeline.scriptwriter import ScriptWriter
from app.providers.base import ProviderResult

pytestmark = pytest.mark.asyncio


# ── 测试替身 ─────────────────────────────────────────────


class FakeLLM:
    """模拟 ZhipuLLMProvider.chat 的测试替身。

    依据 user 消息内容区分「课程元信息」与「知识点」两类调用。
    """

    def __init__(
        self,
        meta_payload: dict,
        kp_payload: dict,
        kp_malformed: bool = False,
    ) -> None:
        self._meta = meta_payload
        self._kp = kp_payload
        self._kp_malformed = kp_malformed
        self.calls = 0

    async def chat(
        self,
        messages,
        *,
        temperature: float = 0.6,
        max_tokens: int = 4096,
        response_format=None,
        thinking_disabled: bool = True,
    ) -> ProviderResult:
        self.calls += 1
        user = messages[-1]["content"]
        if "课程提纲" in user:
            content = json.dumps(self._meta, ensure_ascii=False)
        elif self._kp_malformed:
            content = "对不起，我无法输出 JSON。"
        else:
            content = json.dumps(self._kp, ensure_ascii=False)
        return ProviderResult(task_id="fake", status="completed", content=content)


def _make_draft() -> CourseIR:
    """构造一个 2 分镜的草稿 IR。"""
    scene1 = SceneIR(
        order=1,
        scene_type=SceneType.SLIDE,
        narration_text="原始文字一",
        subtitle_text="原始文字一",
        visual_spec=VisualSpec(slide_ref="slide_1.png"),
        source_page=1,
    )
    scene2 = SceneIR(
        order=2,
        scene_type=SceneType.SLIDE,
        narration_text="原始   文字\n二",
        subtitle_text="",
        visual_spec=VisualSpec(slide_ref="slide_2.png"),
        source_page=2,
    )
    kp = KnowledgePointIR(
        title="知识点甲",
        key_points=["要点1"],
        scenes=[scene1, scene2],
    )
    chapter = ChapterIR(title="第一章", order=1, knowledge_points=[kp])
    return CourseIR(title="abcd1234_课程名", chapters=[chapter])


_META = {
    "title": "线性代数导论",
    "subject": "数学",
    "grade": "大学一年级",
    "target_audience": "本科生",
}
_KP = {
    "tags": ["标签A", "标签B"],
    "quiz_seeds": [
        {
            "question": "矩阵的定义是什么？",
            "question_type": "short",
            "answer": "按矩形排列的数表",
            "explanation": "略",
        }
    ],
    "scenes": [
        {
            "order": 1,
            "scene_type": "generative_clip",
            "narration_text": "口语化讲稿一",
            "subtitle_text": "字幕一",
            "gen_prompt": "数学课堂、粉笔风格",
            "latex_steps": [],
        },
        {
            "order": 2,
            "scene_type": "formula_animation",
            "narration_text": "口语化讲稿二",
            "subtitle_text": "字幕二",
            "gen_prompt": "",
            "latex_steps": ["a = b", "b = c"],
        },
    ],
}


# ── 测试 ─────────────────────────────────────────────────


async def test_enhance_merges_and_preserves_structure() -> None:
    """LLM 结果正确合并，且保留 scene_id / slide_ref 等结构字段。"""
    draft = _make_draft()
    orig_s1_id = draft.chapters[0].knowledge_points[0].scenes[0].scene_id
    orig_s2_id = draft.chapters[0].knowledge_points[0].scenes[1].scene_id

    writer = ScriptWriter(FakeLLM(_META, _KP))
    result = await writer.enhance_ir(draft)

    # 课程元信息
    assert result.title == "线性代数导论"
    assert result.subject == "数学"
    assert result.grade == "大学一年级"
    assert result.target_audience == "本科生"

    kp = result.chapters[0].knowledge_points[0]
    assert kp.tags == ["标签A", "标签B"]
    assert len(kp.quiz_seeds) == 1
    assert kp.quiz_seeds[0].question == "矩阵的定义是什么？"

    s1, s2 = kp.scenes
    # 结构字段保留
    assert s1.scene_id == orig_s1_id
    assert s2.scene_id == orig_s2_id
    assert s1.visual_spec.slide_ref == "slide_1.png"
    assert s1.source_page == 1
    # 文本与类型被覆盖
    assert s1.narration_text == "口语化讲稿一"
    assert s1.subtitle_text == "字幕一"
    assert s1.scene_type == SceneType.GENERATIVE_CLIP
    assert s1.visual_spec.gen_prompt == "数学课堂、粉笔风格"
    assert s1.kp_tags == ["标签A", "标签B"]
    # 公式分镜
    assert s2.scene_type == SceneType.FORMULA_ANIMATION
    assert s2.visual_spec.latex_steps == ["a = b", "b = c"]


async def test_does_not_mutate_input() -> None:
    """enhance_ir 在副本上操作，不改动入参 IR。"""
    draft = _make_draft()
    writer = ScriptWriter(FakeLLM(_META, _KP))
    await writer.enhance_ir(draft)
    # 原 IR 未被改写
    assert draft.title == "abcd1234_课程名"
    assert (
        draft.chapters[0].knowledge_points[0].scenes[0].narration_text == "原始文字一"
    )


async def test_malformed_kp_keeps_original() -> None:
    """单个知识点 JSON 非法 → 保留原文，整体不崩。"""
    draft = _make_draft()
    writer = ScriptWriter(FakeLLM(_META, _KP, kp_malformed=True))
    result = await writer.enhance_ir(draft)

    # 元信息仍然成功
    assert result.subject == "数学"
    # 知识点分镜保留原始内容
    s1 = result.chapters[0].knowledge_points[0].scenes[0]
    assert s1.narration_text == "原始文字一"
    assert s1.scene_type == SceneType.SLIDE


async def test_no_provider_local_fallback() -> None:
    """无 LLM Provider → 本地轻量规整（清理标题、折叠空白、补字幕）。"""
    draft = _make_draft()
    writer = ScriptWriter(None)
    result = await writer.enhance_ir(draft)

    # 标题去掉 8 位 hex 前缀
    assert result.title == "课程名"
    s2 = result.chapters[0].knowledge_points[0].scenes[1]
    # 空白折叠
    assert s2.narration_text == "原始 文字 二"
    # 空字幕补齐为讲稿
    assert s2.subtitle_text == "原始 文字 二"


async def test_progress_callback_invoked() -> None:
    """进度回调按知识点被调用，最终 done == total。"""
    draft = _make_draft()
    seen: list[tuple[int, int]] = []

    async def cb(done: int, total: int) -> None:
        seen.append((done, total))

    writer = ScriptWriter(FakeLLM(_META, _KP))
    await writer.enhance_ir(draft, progress_cb=cb)

    assert seen[-1] == (1, 1)  # 1 个知识点
