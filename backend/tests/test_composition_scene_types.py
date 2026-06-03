"""CompositionService 按画面类型分发的路由测试。

monkeypatch 所有 ffmpeg 原子操作（记录调用），注入 FakeTTS/FakeFormula/FakeVideoGen，
验证四类 scene_type 各走对应画面通路，并在失败/未启用时降级课件页。
"""

import json
from pathlib import Path

import pytest
from sqlalchemy import select

import app.utils.ffmpeg as ffmpeg_mod
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
from app.models.task import SubTask, Task
from app.services.composition_service import CompositionService
from app.services.parser_service import ParserService
from app.utils.hash import compute_input_hash


class FakeTTS:
    provider_name = "fake_tts"

    async def synthesize(self, text: str, output_path: str, *, voice=None) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"audio")
        return output_path


class FakeFormula:
    async def render(self, steps, output_path, *, duration=None) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"formula")
        return output_path


class BoomFormula:
    async def render(self, steps, output_path, *, duration=None) -> str:
        raise RuntimeError("manim 与图片显影都失败")


class FakeVideoGen:
    provider_name = "cogvideox:fake"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate(self, prompt: str, output_path: str, *, image_url=None) -> str:
        self.calls.append(prompt)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"gen")
        return output_path

    def estimate_cost(self, request: dict) -> float:
        return 0.0


@pytest.fixture
def rec_ffmpeg(monkeypatch):
    calls = {
        k: 0
        for k in (
            "probe",
            "image_audio",
            "video_audio",
            "kenburns",
            "pip",
            "concat",
            "mux",
        )
    }

    async def probe(path: str) -> float:
        calls["probe"] += 1
        return 2.0

    async def img(image, audio, out, **kw) -> str:
        calls["image_audio"] += 1
        Path(out).write_bytes(b"c")
        return out

    async def vid(video, audio, out, **kw) -> str:
        calls["video_audio"] += 1
        Path(out).write_bytes(b"c")
        return out

    async def kb(image, audio, out, **kw) -> str:
        calls["kenburns"] += 1
        Path(out).write_bytes(b"c")
        return out

    async def pip(bg, fg, audio, out, **kw) -> str:
        calls["pip"] += 1
        Path(out).write_bytes(b"c")
        return out

    async def concat(clips, out, **kw) -> str:
        calls["concat"] += 1
        Path(out).write_bytes(b"v")
        return out

    async def mux(video, out, **kw) -> str:
        calls["mux"] += 1
        Path(out).write_bytes(b"v")
        return out

    monkeypatch.setattr(ffmpeg_mod, "probe_duration", probe)
    monkeypatch.setattr(ffmpeg_mod, "image_audio_to_clip", img)
    monkeypatch.setattr(ffmpeg_mod, "video_audio_to_clip", vid)
    monkeypatch.setattr(ffmpeg_mod, "image_to_kenburns_clip", kb)
    monkeypatch.setattr(ffmpeg_mod, "overlay_pip_clip", pip)
    monkeypatch.setattr(ffmpeg_mod, "concat_clips", concat)
    monkeypatch.setattr(ffmpeg_mod, "mux_subtitle_and_chapters", mux)
    return calls


async def _seed(db, scene: SceneIR, *, config: dict | None = None) -> tuple[str, str]:
    project = Project(title="t", status="reviewing")
    db.add(project)
    await db.flush()
    task = Task(
        project_id=project.id,
        task_type="full_pipeline",
        status="generating",
        config_json=(json.dumps(config) if config else None),
    )
    db.add(task)
    await db.flush()
    await db.commit()
    pid, tid = str(project.id), str(task.id)
    kp = KnowledgePointIR(title="kp", key_points=["要点"], scenes=[scene])
    ch = ChapterIR(title="ch", order=1, knowledge_points=[kp])
    ir = CourseIR(course_id=pid, title="c", version=1, chapters=[ch])
    await ParserService().save_ir(ir, pid, version=1)
    return pid, tid


async def _subtasks(db, tid: str) -> list[SubTask]:
    import uuid

    rows = await db.execute(select(SubTask).where(SubTask.task_id == uuid.UUID(tid)))
    return list(rows.scalars().all())


# ── 公式 ─────────────────────────────────────────────────


async def test_formula_routes_to_video_clip(
    db_session, tmp_path, monkeypatch, rec_ffmpeg
):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    scene = SceneIR(
        order=1,
        scene_type=SceneType.FORMULA_ANIMATION,
        narration_text="推导",
        visual_spec=VisualSpec(latex_steps=["a=b", "b=c"]),
    )
    pid, tid = await _seed(db_session, scene)
    await CompositionService(
        tts_provider=FakeTTS(), formula_renderer=FakeFormula()
    ).compose(pid, tid, db_session)

    assert rec_ffmpeg["video_audio"] == 1
    assert rec_ffmpeg["image_audio"] == 0
    subs = await _subtasks(db_session, tid)
    formula = [s for s in subs if s.subtask_type == "formula"]
    assert formula and formula[0].status == "completed"


async def test_formula_failure_degrades_to_slide(
    db_session, tmp_path, monkeypatch, rec_ffmpeg
):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    scene = SceneIR(
        order=1,
        scene_type=SceneType.FORMULA_ANIMATION,
        narration_text="推导",
        visual_spec=VisualSpec(latex_steps=["a=b"]),
    )
    pid, tid = await _seed(db_session, scene)
    await CompositionService(
        tts_provider=FakeTTS(), formula_renderer=BoomFormula()
    ).compose(pid, tid, db_session)

    # 公式失败 → 课件页静图兜底
    assert rec_ffmpeg["image_audio"] == 1
    subs = await _subtasks(db_session, tid)
    assert any(s.subtask_type == "formula" and s.status == "failed" for s in subs)
    assert any(s.subtask_type == "render" and s.status == "completed" for s in subs)


# ── 数字人 ───────────────────────────────────────────────


async def test_digital_human_local_pip(db_session, tmp_path, monkeypatch, rec_ffmpeg):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    scene = SceneIR(
        order=1, scene_type=SceneType.DIGITAL_HUMAN, narration_text="引入讲解"
    )
    pid, tid = await _seed(db_session, scene, config={"use_digital_human": True})
    await CompositionService(tts_provider=FakeTTS()).compose(pid, tid, db_session)

    assert rec_ffmpeg["pip"] == 1  # 走画中画叠加
    subs = await _subtasks(db_session, tid)
    dh = [s for s in subs if s.subtask_type == "digital_human"]
    assert dh and dh[0].status == "completed"
    assert dh[0].provider_name == "local_digital_human"


async def test_digital_human_disabled_degrades_to_slide(
    db_session, tmp_path, monkeypatch, rec_ffmpeg
):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    scene = SceneIR(
        order=1, scene_type=SceneType.DIGITAL_HUMAN, narration_text="引入讲解"
    )
    pid, tid = await _seed(db_session, scene, config={"use_digital_human": False})
    await CompositionService(tts_provider=FakeTTS()).compose(pid, tid, db_session)

    assert rec_ffmpeg["pip"] == 0
    assert rec_ffmpeg["image_audio"] == 1  # 纯课件页
    subs = await _subtasks(db_session, tid)
    assert any(s.subtask_type == "render" for s in subs)
    assert not any(s.subtask_type == "digital_human" for s in subs)


# ── 生成式片段 ───────────────────────────────────────────


async def test_generative_kenburns_fallback_when_disabled(
    db_session, tmp_path, monkeypatch, rec_ffmpeg
):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    scene = SceneIR(
        order=1,
        scene_type=SceneType.GENERATIVE_CLIP,
        narration_text="概念",
        visual_spec=VisualSpec(gen_prompt="数学课堂、粉笔风格 片头"),
    )
    fvg = FakeVideoGen()
    pid, tid = await _seed(db_session, scene, config={"use_generative": False})
    await CompositionService(tts_provider=FakeTTS(), video_gen_provider=fvg).compose(
        pid, tid, db_session
    )

    assert rec_ffmpeg["kenburns"] == 1  # 运镜兜底
    assert fvg.calls == []  # 未调真生成
    subs = await _subtasks(db_session, tid)
    vg = [s for s in subs if s.subtask_type == "video_gen"]
    assert vg and vg[0].provider_name == "kenburns_fallback"


async def test_generative_uses_provider_when_enabled(
    db_session, tmp_path, monkeypatch, rec_ffmpeg
):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    scene = SceneIR(
        order=1,
        scene_type=SceneType.GENERATIVE_CLIP,
        narration_text="概念",
        visual_spec=VisualSpec(gen_prompt="抽象概念 情景镜头"),
    )
    fvg = FakeVideoGen()
    pid, tid = await _seed(db_session, scene, config={"use_generative": True})
    await CompositionService(tts_provider=FakeTTS(), video_gen_provider=fvg).compose(
        pid, tid, db_session
    )

    assert fvg.calls == ["抽象概念 情景镜头"]  # 调用了真生成
    assert rec_ffmpeg["video_audio"] == 1
    assert rec_ffmpeg["kenburns"] == 0
    subs = await _subtasks(db_session, tid)
    vg = [s for s in subs if s.subtask_type == "video_gen"]
    assert vg and vg[0].provider_name == "cogvideox:fake"


async def test_generative_cache_hit_skips_generate(
    db_session, tmp_path, monkeypatch, rec_ffmpeg
):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    prompt = "已缓存的提示词"
    # 预置缓存命中文件
    key = compute_input_hash(f"{settings.COGVIDEO_MODEL}|{prompt}")
    cache_dir = tmp_path / "_cache" / "video_gen"
    cache_dir.mkdir(parents=True)
    (cache_dir / f"{key}.mp4").write_bytes(b"cached")

    scene = SceneIR(
        order=1,
        scene_type=SceneType.GENERATIVE_CLIP,
        narration_text="概念",
        visual_spec=VisualSpec(gen_prompt=prompt),
    )
    fvg = FakeVideoGen()
    pid, tid = await _seed(db_session, scene, config={"use_generative": True})
    await CompositionService(tts_provider=FakeTTS(), video_gen_provider=fvg).compose(
        pid, tid, db_session
    )

    assert fvg.calls == []  # 命中缓存，未重复付费
    assert rec_ffmpeg["video_audio"] == 1
