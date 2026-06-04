"""CompositionService 测试。

注入 FakeTTS + monkeypatch app.utils.ffmpeg 的原子操作，使用真实 Pillow 渲染，
全程不依赖真实 FFmpeg / 网络。覆盖 IR 展平、SubTask/Resource 落库、字幕时间轴、
TTS 失败与无旁白的静音降级。
"""

from pathlib import Path

import pytest
from sqlalchemy import select

from app.config import settings
from app.ir.schema import (
    ChapterIR,
    CourseIR,
    KnowledgePointIR,
    SceneIR,
    SceneType,
    VisualSpec,
)
from app.models.project import Project
from app.models.resource import Resource
from app.models.task import SubTask, Task
from app.pipeline.renderer import SlideRenderer
from app.services.composition_service import (
    CompositionService,
    _chapter_spans,
    _flatten,
    _real_slide,
)
from app.services.parser_service import ParserService
from app.utils import ffmpeg as ffmpeg_mod


def _uuid(value: str):
    import uuid

    return uuid.UUID(value)


# ── 测试替身 ─────────────────────────────────────────────


class FakeTTS:
    provider_name = "fake_tts"

    def __init__(self) -> None:
        self.synthesized: list[str] = []
        self.voices: list[str | None] = []

    async def synthesize(self, text: str, output_path: str, *, voice=None) -> str:
        if "FAIL" in text:
            raise RuntimeError("模拟配音失败")
        self.synthesized.append(text)
        self.voices.append(voice)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-audio")
        return output_path


class FakeFormula:
    """假公式渲染器：写占位 mp4，避免在合成测试里跑真实 matplotlib。"""

    async def render(self, steps, output_path: str, *, duration=None) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"formula")
        return output_path


class SpyRenderer(SlideRenderer):
    """记录分镜渲染收到的字幕文本，仍使用真实 Pillow 产图。"""

    def __init__(self) -> None:
        super().__init__()
        self.scene_subtitles: list[str] = []

    def render_scene(self, **kwargs) -> str:
        self.scene_subtitles.append(kwargs.get("subtitle", ""))
        return super().render_scene(**kwargs)


@pytest.fixture
def fake_ffmpeg(monkeypatch):
    """把 ffmpeg 原子操作替换为产出占位文件、固定时长 2.0s。"""

    async def fake_probe(path: str) -> float:
        return 2.0

    async def fake_clip(image, audio, out, **kw) -> str:
        Path(out).write_bytes(b"clip")
        return out

    async def fake_concat(clips, out) -> str:
        Path(out).write_bytes(b"video")
        return out

    async def fake_mux(video, out, *, srt_path=None, chapter_metadata_path=None) -> str:
        Path(out).write_bytes(b"muxed-video")
        return out

    async def fake_video_clip(video, audio, out, **kw) -> str:
        Path(out).write_bytes(b"clip")
        return out

    async def fake_kenburns(image, audio, out, **kw) -> str:
        Path(out).write_bytes(b"clip")
        return out

    async def fake_pip(bg, fg, audio, out, **kw) -> str:
        Path(out).write_bytes(b"clip")
        return out

    monkeypatch.setattr(ffmpeg_mod, "probe_duration", fake_probe)
    monkeypatch.setattr(ffmpeg_mod, "image_audio_to_clip", fake_clip)
    monkeypatch.setattr(ffmpeg_mod, "concat_clips", fake_concat)
    monkeypatch.setattr(ffmpeg_mod, "mux_subtitle_and_chapters", fake_mux)
    monkeypatch.setattr(ffmpeg_mod, "video_audio_to_clip", fake_video_clip)
    monkeypatch.setattr(ffmpeg_mod, "image_to_kenburns_clip", fake_kenburns)
    monkeypatch.setattr(ffmpeg_mod, "overlay_pip_clip", fake_pip)


def _make_ir(project_id: str) -> CourseIR:
    s1 = SceneIR(
        order=1,
        scene_type=SceneType.SLIDE,
        narration_text="第一段讲解内容。这里继续补充说明。",
        subtitle_text="旧字幕不应进入成片",
    )
    s2 = SceneIR(
        order=2,
        scene_type=SceneType.FORMULA_ANIMATION,
        narration_text="推导过程讲解。",
        subtitle_text="推导字幕",
        visual_spec=VisualSpec(latex_steps=["a = b", "b = c"]),
    )
    kp1 = KnowledgePointIR(
        title="知识点一", key_points=["要点A", "要点B"], scenes=[s1, s2]
    )
    ch1 = ChapterIR(title="第一章", order=1, knowledge_points=[kp1])

    # 无旁白 → 静音降级
    s3 = SceneIR(
        order=1,
        scene_type=SceneType.SLIDE,
        narration_text="",
        subtitle_text="无旁白字幕",
    )
    # 触发配音失败 → 静音降级
    s4 = SceneIR(
        order=2,
        scene_type=SceneType.DIGITAL_HUMAN,
        narration_text="FAIL 这段会让配音抛错",
        subtitle_text="失败降级字幕",
    )
    kp2 = KnowledgePointIR(title="知识点二", scenes=[s3, s4])
    ch2 = ChapterIR(title="第二章", order=2, knowledge_points=[kp2])

    return CourseIR(
        course_id=project_id,
        title="测试课程",
        subject="数学",
        grade="大一",
        version=1,
        chapters=[ch1, ch2],
    )


async def _seed(db) -> tuple[str, str]:
    project = Project(title="测试课程", status="reviewing")
    db.add(project)
    await db.flush()
    task = Task(
        project_id=project.id,
        task_type="full_pipeline",
        status="reviewing",
        progress=60,
    )
    db.add(task)
    await db.flush()
    await db.commit()
    return str(project.id), str(task.id)


# ── 纯函数 ───────────────────────────────────────────────


def test_flatten_orders_by_chapter_kp_scene() -> None:
    ir = _make_ir("pid")
    flat = _flatten(ir)
    assert [fs.scene.subtitle_text for fs in flat] == [
        "旧字幕不应进入成片",
        "推导字幕",
        "无旁白字幕",
        "失败降级字幕",
    ]
    assert [fs.chapter_index for fs in flat] == [0, 0, 1, 1]


def test_chapter_spans() -> None:
    ir = _make_ir("pid")
    flat = _flatten(ir)
    # 模拟时间轴：每镜 2 秒
    cursor = 0.0
    for fs in flat:
        fs.start = cursor
        fs.end = cursor + 2.0
        cursor = fs.end
    spans = _chapter_spans(flat)
    assert spans == [(0.0, 4.0, "第一章"), (4.0, 8.0, "第二章")]


# ── 端到端（mock）合成 ───────────────────────────────────


async def test_compose_full_flow(db_session, tmp_path, monkeypatch, fake_ffmpeg):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    project_id, task_id = await _seed(db_session)

    ir = _make_ir(project_id)
    await ParserService().save_ir(ir, project_id, version=1)

    fake_tts = FakeTTS()
    spy_renderer = SpyRenderer()
    await CompositionService(
        tts_provider=fake_tts, renderer=spy_renderer, formula_renderer=FakeFormula()
    ).compose(project_id, task_id, db_session)

    # 任务与项目状态
    task = await db_session.get(Task, _uuid(task_id))
    assert task is not None
    assert task.status == "completed"
    assert task.progress == 100

    project = await db_session.get(Project, _uuid(project_id))
    assert project.status == "completed"

    # 产物文件（按生成版本 gen{N} 命名）
    out = tmp_path / project_id / "output"
    assert (out / "gen1.mp4").exists()
    assert (out / "gen1.srt").exists()
    assert (out / "gen1.vtt").exists()
    assert (out / "gen1_cover.png").exists()
    assert (tmp_path / project_id / "export" / "gen1.zip").exists()
    # workspace 已清理
    assert not (tmp_path / project_id / "workspace" / task_id).exists()

    # 资源入库
    resources = (await db_session.execute(select(Resource))).scalars().all()
    types = sorted(r.resource_type for r in resources)
    assert types == ["archive", "image", "subtitle", "subtitle", "video"]
    video = next(r for r in resources if r.resource_type == "video")
    assert video.watermark_applied is True
    assert video.mime_type == "video/mp4"

    # SubTask：按画面类型分发——s1/s3 课件页(render)、s2 公式(formula)、
    # s4 数字人(digital_human，本地讲师默认开)；tts 仅对有旁白且成功/失败者
    subtasks = (await db_session.execute(select(SubTask))).scalars().all()
    renders = [s for s in subtasks if s.subtask_type == "render"]
    formulas = [s for s in subtasks if s.subtask_type == "formula"]
    dhs = [s for s in subtasks if s.subtask_type == "digital_human"]
    ttss = [s for s in subtasks if s.subtask_type == "tts"]
    assert len(renders) == 2  # s1、s3
    assert all(s.status == "completed" for s in renders)
    assert len(formulas) == 1 and formulas[0].status == "completed"  # s2
    assert len(dhs) == 1 and dhs[0].status == "completed"  # s4（旁白失败仍出画中画）
    # s1、s2 成功；s4 失败；s3 无旁白不产生 tts
    assert sorted(s.status for s in ttss) == ["completed", "completed", "failed"]
    assert fake_tts.synthesized == [
        "第一段讲解内容。这里继续补充说明。",
        "推导过程讲解。",
    ]
    assert spy_renderer.scene_subtitles
    assert all(subtitle == "" for subtitle in spy_renderer.scene_subtitles)

    # 字幕时间轴：以旁白切句生成，旧 subtitle_text 不进入成片
    srt = (out / "gen1.srt").read_text(encoding="utf-8")
    assert "00:00:00,000 --> " in srt
    assert "00:00:02,000 --> 00:00:04,000" in srt
    assert "00:00:08,000 --> 00:00:12,000" in srt
    assert "第一段讲解内容。" in srt
    assert "这里继续补充说明。" in srt
    assert "推导过程讲解。" in srt
    assert "FAIL 这段会让配音抛错" in srt
    assert "旧字幕不应进入成片" not in srt
    assert "无旁白字幕" not in srt


async def test_compose_missing_ir_marks_failed(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    project_id, task_id = await _seed(db_session)
    # 不保存 IR
    await CompositionService(tts_provider=FakeTTS()).compose(
        project_id, task_id, db_session
    )
    task = await db_session.get(Task, _uuid(task_id))
    assert task.status == "failed"


def test_real_slide_helper(tmp_path) -> None:
    from PIL import Image

    real = tmp_path / "page_1.png"
    Image.new("RGB", (10, 10), (0, 0, 0)).save(real)
    scene_real = SceneIR(
        order=1, scene_type=SceneType.SLIDE, visual_spec=VisualSpec(slide_ref=str(real))
    )
    scene_placeholder = SceneIR(
        order=1,
        scene_type=SceneType.SLIDE,
        visual_spec=VisualSpec(slide_ref="slide_1.png"),
    )
    assert _real_slide(scene_real) == str(real)
    assert _real_slide(scene_placeholder) is None


async def test_compose_with_real_slide_background(
    db_session, tmp_path, monkeypatch, fake_ffmpeg
):
    """某分镜 slide_ref 指向真实页图时，合成仍成功出片。"""
    from PIL import Image

    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    project_id, task_id = await _seed(db_session)

    bg = tmp_path / "real_page.png"
    Image.new("RGB", (1280, 720), (20, 40, 80)).save(bg)

    s1 = SceneIR(
        order=1,
        scene_type=SceneType.SLIDE,
        narration_text="讲解。",
        subtitle_text="字幕",
        visual_spec=VisualSpec(slide_ref=str(bg)),
    )
    kp = KnowledgePointIR(title="知识点", scenes=[s1])
    ch = ChapterIR(title="章", order=1, knowledge_points=[kp])
    ir = CourseIR(course_id=project_id, title="真页图课程", version=1, chapters=[ch])
    await ParserService().save_ir(ir, project_id, version=1)

    await CompositionService(tts_provider=FakeTTS()).compose(
        project_id, task_id, db_session
    )

    task = await db_session.get(Task, _uuid(task_id))
    assert task.status == "completed"
    renders = [
        s
        for s in (await db_session.execute(select(SubTask))).scalars().all()
        if s.subtask_type == "render"
    ]
    assert renders and all(s.status == "completed" for s in renders)


async def test_regenerate_produces_new_version(
    db_session, tmp_path, monkeypatch, fake_ffmpeg
):
    """重新生成产出独立版本 gen2，视频资源 version 递增、记录 ir_version。"""
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    project_id, task_id = await _seed(db_session)
    await ParserService().save_ir(_make_ir(project_id), project_id, version=1)

    # 第一次生成 → gen1
    await CompositionService(
        tts_provider=FakeTTS(), formula_renderer=FakeFormula()
    ).compose(project_id, task_id, db_session)
    # 第二次生成（新任务）→ gen2
    task2 = Task(
        project_id=_uuid(project_id), task_type="full_pipeline", status="generating"
    )
    db_session.add(task2)
    await db_session.flush()
    await db_session.commit()
    await CompositionService(
        tts_provider=FakeTTS(), formula_renderer=FakeFormula()
    ).compose(project_id, str(task2.id), db_session)

    videos = [
        r
        for r in (await db_session.execute(select(Resource))).scalars().all()
        if r.resource_type == "video"
    ]
    assert sorted(v.version for v in videos) == [1, 2]
    assert (tmp_path / project_id / "output" / "gen2.mp4").exists()
    # 视频资源记录了生成时的 IR 版本
    import json as _json

    metas = [_json.loads(v.metadata_json or "{}") for v in videos]
    assert all(m.get("ir_version") == 1 for m in metas)


async def test_tts_voice_from_task_config(
    db_session, tmp_path, monkeypatch, fake_ffmpeg
):
    """approve 写入的 config.tts_voice 透传到 TTS synthesize。"""
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))

    project = Project(title="音色测试", status="reviewing")
    db_session.add(project)
    await db_session.flush()
    task = Task(
        project_id=project.id,
        task_type="full_pipeline",
        status="generating",
        config_json='{"tts_voice": "zh-CN-YunxiNeural"}',
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.commit()
    pid, tid = str(project.id), str(task.id)
    await ParserService().save_ir(_make_ir(pid), pid, version=1)

    fake_tts = FakeTTS()
    await CompositionService(
        tts_provider=fake_tts, formula_renderer=FakeFormula()
    ).compose(pid, tid, db_session)

    assert fake_tts.voices  # 有配音调用
    assert all(v == "zh-CN-YunxiNeural" for v in fake_tts.voices)
