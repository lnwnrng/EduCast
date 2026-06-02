"""合成编排服务 — 模块三核心。

消费教师审核后的 IR，逐分镜「配音(Edge-TTS) + 课件页渲染(Pillow)」，再用
FFmpeg 拼接为带字幕/章节/水印的 MP4，连同 SRT/VTT/封面/IR 打包入库。

设计要点（沿用 scriptwriter_service 的服务范式）:
- **课件优先 + 降级**: 非 slide 分镜（数字人/生成式/公式）P1 统一降级为课件页
  渲染；TTS 失败或无旁白时降级为静音分镜，保证仍能出片。
- **可观测**: 每个分镜的渲染/配音各记一条 SubTask。
- **可注入**: tts_provider / renderer / composer 可注入，FFmpeg 原子操作集中在
  app.utils.ffmpeg，单元测试通过 monkeypatch 脱离真实 FFmpeg 与网络。
"""

import logging
import os
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ir.schema import CourseIR, KnowledgePointIR, SceneIR, SceneType
from app.models.project import Project
from app.models.task import SubTask, Task
from app.pipeline.composer import VideoComposer
from app.pipeline.renderer import SlideRenderer
from app.pipeline.subtitles import (
    build_chapter_metadata,
    build_srt,
    build_vtt,
)
from app.providers.tts import get_tts_provider
from app.services.parser_service import ParserService
from app.services.resource_service import ResourceService
from app.utils import ffmpeg

logger = logging.getLogger(__name__)

_BADGES: dict[SceneType, str | None] = {
    SceneType.SLIDE: None,
    SceneType.FORMULA_ANIMATION: "公式推导",
    SceneType.DIGITAL_HUMAN: "讲解",
    SceneType.GENERATIVE_CLIP: "概念演示",
}

_SENTENCE_SPLIT = re.compile(r"[。！？!?\n]+")


@dataclass
class _FlatScene:
    """展平后的分镜（携带所属知识点与章节信息）。"""

    scene: SceneIR
    kp: KnowledgePointIR
    chapter_index: int
    chapter_title: str
    # 运行期填充
    start: float = 0.0
    end: float = 0.0
    subtitle: str = field(default="")


class CompositionService:
    """教学视频合成编排服务。"""

    def __init__(
        self,
        *,
        tts_provider=None,
        renderer: SlideRenderer | None = None,
        composer: VideoComposer | None = None,
    ) -> None:
        self._parser_service = ParserService()
        self._tts = tts_provider if tts_provider is not None else get_tts_provider()
        self._renderer = renderer or SlideRenderer()
        self._composer = composer or VideoComposer()

    # ── 入口 ──────────────────────────────────────────────────

    async def compose(
        self,
        project_id: str,
        task_id: str,
        db: AsyncSession,
    ) -> None:
        """执行完整合成流程。"""
        ir = await self._parser_service.load_ir(project_id)
        if ir is None:
            logger.error("合成找不到 IR: project=%s", project_id)
            await self._update_task(
                db, task_id, "failed", 0, error_message="合成失败：未找到 IR"
            )
            await self._update_project(db, project_id, "failed")
            return

        flat = _flatten(ir)
        if not flat:
            await self._update_task(
                db, task_id, "failed", 0, error_message="合成失败：IR 无分镜"
            )
            await self._update_project(db, project_id, "failed")
            return

        try:
            await self._update_task(db, task_id, "generating", 50)
            await self._update_project(db, project_id, "generating")

            root = settings.STORAGE_ROOT
            workspace = os.path.join(root, project_id, "workspace", task_id)
            output_dir = os.path.join(root, project_id, "output")
            export_dir = os.path.join(root, project_id, "export")
            os.makedirs(workspace, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(export_dir, exist_ok=True)

            watermark = settings.WATERMARK_TEXT or ir.title or "课影 EduCast"
            task_uuid = _to_uuid(task_id)

            # ── 逐分镜：渲染 + 配音 + 单镜片段 ──
            clip_paths: list[str] = []
            cursor = 0.0
            total = len(flat)
            for i, fs in enumerate(flat):
                clip = await self._build_scene_clip(
                    db, task_uuid, fs, i, workspace, watermark
                )
                if clip is None:
                    continue
                clip_path, duration = clip
                fs.start = cursor
                fs.end = cursor + duration
                cursor = fs.end
                fs.subtitle = (
                    fs.scene.subtitle_text or fs.scene.narration_text
                ).strip()
                clip_paths.append(clip_path)

                progress = 50 + int(30 * (i + 1) / total)
                await self._update_task(db, task_id, "generating", progress)

            if not clip_paths:
                raise RuntimeError("所有分镜片段生成失败")

            # ── 字幕 / 章节 ──
            await self._update_task(db, task_id, "composing", 82)
            segments = [(fs.start, fs.end, fs.subtitle) for fs in flat if fs.subtitle]
            chapters = _chapter_spans(flat)

            srt_path = os.path.join(output_dir, f"v{ir.version}.srt")
            vtt_path = os.path.join(output_dir, f"v{ir.version}.vtt")
            chapter_path = os.path.join(workspace, "chapters.txt")
            _write(srt_path, build_srt(segments))
            _write(vtt_path, build_vtt(segments))
            _write(chapter_path, build_chapter_metadata(chapters))

            # ── FFmpeg 合成 ──
            video_path = os.path.join(output_dir, f"v{ir.version}.mp4")
            await self._composer.compose(
                clip_paths,
                video_path,
                srt_path=srt_path,
                chapter_metadata_path=chapter_path,
            )

            # ── 封面 ──
            cover_path = os.path.join(output_dir, f"v{ir.version}_cover.png")
            self._renderer.render_cover(
                title=ir.title or "教学视频",
                subject=ir.subject,
                grade=ir.grade,
                output_path=cover_path,
            )

            # ── zip 打包 ──
            await self._update_task(db, task_id, "composing", 92)
            zip_path = os.path.join(export_dir, f"v{ir.version}.zip")
            _bundle_zip(zip_path, ir, video_path, srt_path, vtt_path, cover_path)

            # ── 入库 ──
            await self._register_resources(
                db,
                project_id,
                ir,
                video_path=video_path,
                srt_path=srt_path,
                vtt_path=vtt_path,
                cover_path=cover_path,
                zip_path=zip_path,
            )

            # ── 收尾 ──
            actual_cost = await self._sum_subtask_cost(db, task_uuid)
            await self._update_task(
                db,
                task_id,
                "completed",
                100,
                ir_snapshot_path=video_path,
                actual_cost=actual_cost,
            )
            await self._update_project(db, project_id, "completed")
            shutil.rmtree(workspace, ignore_errors=True)
            logger.info(
                "合成完成: project=%s, video=%s, 分镜=%d, 时长≈%.1fs",
                project_id,
                video_path,
                len(clip_paths),
                cursor,
            )

        except Exception as exc:  # noqa: BLE001 — 顶层兜底，置失败状态
            logger.error(
                "合成失败: project=%s, error=%s", project_id, exc, exc_info=True
            )
            await self._update_task(
                db, task_id, "failed", 0, error_message=f"合成失败: {exc}"
            )
            await self._update_project(db, project_id, "failed")

    # ── 单分镜片段 ────────────────────────────────────────────

    async def _build_scene_clip(
        self,
        db: AsyncSession,
        task_uuid: UUID | None,
        fs: _FlatScene,
        index: int,
        workspace: str,
        watermark: str,
    ) -> tuple[str, float] | None:
        """渲染底图 + 配音 + 合成单镜片段，返回 (片段路径, 时长)。失败返回 None。"""
        scene = fs.scene
        image_path = os.path.join(workspace, f"scene_{index}.png")
        audio_path = os.path.join(workspace, f"scene_{index}.mp3")
        clip_path = os.path.join(workspace, f"clip_{index}.mp4")

        # 1. 渲染课件底图
        try:
            self._renderer.render_scene(
                title=fs.kp.title or "教学内容",
                body_lines=_body_lines(scene, fs.kp),
                subtitle=(scene.subtitle_text or scene.narration_text).strip(),
                image_path=_first_image(scene),
                output_path=image_path,
                watermark=watermark,
                badge=_BADGES.get(scene.scene_type),
                background_path=_real_slide(scene),
            )
            await self._add_subtask(
                db, task_uuid, "render", scene.scene_id, "completed", image_path
            )
        except Exception as exc:  # noqa: BLE001 — 单镜渲染失败则跳过该镜
            logger.warning("分镜 %d 渲染失败，跳过: %s", index, exc)
            await self._add_subtask(
                db, task_uuid, "render", scene.scene_id, "failed", error=str(exc)
            )
            return None

        # 2. 配音（无旁白或失败 → 静音降级）
        narration = (scene.narration_text or "").strip()
        used_audio: str | None = None
        if narration:
            try:
                await self._tts.synthesize(narration, audio_path)
                used_audio = audio_path
                await self._add_subtask(
                    db,
                    task_uuid,
                    "tts",
                    scene.scene_id,
                    "completed",
                    audio_path,
                    provider=getattr(self._tts, "provider_name", "edge_tts"),
                )
            except Exception as exc:  # noqa: BLE001 — 配音失败降级为静音
                logger.warning("分镜 %d 配音失败，降级为静音: %s", index, exc)
                await self._add_subtask(
                    db, task_uuid, "tts", scene.scene_id, "failed", error=str(exc)
                )

        # 3. 时长
        duration = 0.0
        if used_audio:
            duration = await ffmpeg.probe_duration(used_audio)
        if duration <= 0:
            duration = settings.SILENT_SCENE_DURATION

        # 4. 单镜片段
        try:
            await ffmpeg.image_audio_to_clip(
                image_path,
                used_audio,
                clip_path,
                width=settings.VIDEO_WIDTH,
                height=settings.VIDEO_HEIGHT,
                fps=settings.VIDEO_FPS,
                duration=duration,
            )
        except Exception as exc:  # noqa: BLE001 — 片段生成失败则跳过该镜
            logger.warning("分镜 %d 片段生成失败，跳过: %s", index, exc)
            return None

        return clip_path, duration

    # ── 入库 ──────────────────────────────────────────────────

    async def _register_resources(
        self,
        db: AsyncSession,
        project_id: str,
        ir: CourseIR,
        *,
        video_path: str,
        srt_path: str,
        vtt_path: str,
        cover_path: str,
        zip_path: str,
    ) -> None:
        pid = _to_uuid(project_id)
        if pid is None:
            return
        v = ir.version
        await ResourceService.create_resource(
            db,
            pid,
            "video",
            f"{ir.title} 成片 v{v}",
            video_path,
            mime_type="video/mp4",
            version=v,
            watermark_applied=True,
            metadata={"subject": ir.subject, "grade": ir.grade},
        )
        await ResourceService.create_resource(
            db,
            pid,
            "subtitle",
            f"{ir.title} 字幕 SRT v{v}",
            srt_path,
            mime_type="application/x-subrip",
            version=v,
        )
        await ResourceService.create_resource(
            db,
            pid,
            "subtitle",
            f"{ir.title} 字幕 VTT v{v}",
            vtt_path,
            mime_type="text/vtt",
            version=v,
        )
        await ResourceService.create_resource(
            db,
            pid,
            "image",
            f"{ir.title} 封面 v{v}",
            cover_path,
            mime_type="image/png",
            version=v,
        )
        await ResourceService.create_resource(
            db,
            pid,
            "archive",
            f"{ir.title} 打包 v{v}",
            zip_path,
            mime_type="application/zip",
            version=v,
        )

    # ── 状态更新 / SubTask ────────────────────────────────────

    async def _add_subtask(
        self,
        db: AsyncSession,
        task_uuid: UUID | None,
        subtask_type: str,
        scene_id: str,
        status: str,
        result_url: str | None = None,
        *,
        provider: str | None = None,
        error: str | None = None,
    ) -> None:
        if task_uuid is None:
            return
        db.add(
            SubTask(
                task_id=task_uuid,
                subtask_type=subtask_type,
                scene_id=scene_id,
                status=status,
                progress=100 if status == "completed" else 0,
                provider_name=provider,
                result_url=result_url,
                error_message=error,
                cost=0.0,
            )
        )
        await db.flush()

    async def _update_task(
        self,
        db: AsyncSession,
        task_id: str,
        status: str,
        progress: int,
        ir_snapshot_path: str | None = None,
        error_message: str | None = None,
        actual_cost: float | None = None,
    ) -> None:
        pk = _to_uuid(task_id)
        if pk is None:
            return
        task = await db.get(Task, pk)
        if task:
            task.status = status
            task.progress = max(progress, 0)
            if ir_snapshot_path is not None:
                task.ir_snapshot_path = ir_snapshot_path
            if error_message is not None:
                task.error_message = error_message
            if actual_cost is not None:
                task.actual_cost = actual_cost
            await db.commit()

    async def _sum_subtask_cost(
        self, db: AsyncSession, task_uuid: UUID | None
    ) -> float:
        """汇总该任务各子任务实际成本（模块三免费栈为 0，机制供后续复用）。"""
        if task_uuid is None:
            return 0.0
        stmt = select(func.coalesce(func.sum(SubTask.cost), 0.0)).where(
            SubTask.task_id == task_uuid
        )
        return float((await db.execute(stmt)).scalar() or 0.0)

    async def _update_project(
        self, db: AsyncSession, project_id: str, status: str
    ) -> None:
        pk = _to_uuid(project_id)
        if pk is None:
            return
        project = await db.get(Project, pk)
        if project:
            project.status = status
            await db.commit()


# ── 模块级纯函数辅助 ─────────────────────────────────────────


def _flatten(ir: CourseIR) -> list[_FlatScene]:
    """把 IR 展平为按顺序的分镜列表。"""
    flat: list[_FlatScene] = []
    for ci, chapter in enumerate(sorted(ir.chapters, key=lambda c: c.order)):
        for kp in chapter.knowledge_points:
            for scene in sorted(kp.scenes, key=lambda s: s.order):
                flat.append(
                    _FlatScene(
                        scene=scene,
                        kp=kp,
                        chapter_index=ci,
                        chapter_title=chapter.title,
                    )
                )
    return flat


def _chapter_spans(flat: list[_FlatScene]) -> list[tuple[float, float, str]]:
    """按章节聚合时间轴，得到章节标记 (start, end, title)。"""
    spans: list[tuple[float, float, str]] = []
    if not flat:
        return spans
    cur_idx = flat[0].chapter_index
    cur_title = flat[0].chapter_title
    cur_start = flat[0].start
    cur_end = flat[0].end
    for fs in flat[1:]:
        if fs.chapter_index != cur_idx:
            spans.append((cur_start, cur_end, cur_title))
            cur_idx, cur_title, cur_start = (
                fs.chapter_index,
                fs.chapter_title,
                fs.start,
            )
        cur_end = fs.end
    spans.append((cur_start, cur_end, cur_title))
    return spans


def _body_lines(scene: SceneIR, kp: KnowledgePointIR) -> list[str]:
    """决定课件页正文要点。"""
    spec = scene.visual_spec
    if scene.scene_type == SceneType.FORMULA_ANIMATION and spec.latex_steps:
        return spec.latex_steps[:6]
    if scene.scene_type == SceneType.GENERATIVE_CLIP and spec.gen_prompt:
        return [f"画面：{spec.gen_prompt}"]
    if kp.key_points:
        return kp.key_points[:6]
    text = scene.narration_text or scene.subtitle_text
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()][:6]


def _real_slide(scene: SceneIR) -> str | None:
    """slide_ref 指向真实存在的页图时返回其路径（否则 None → 文本合成）。"""
    ref = scene.visual_spec.slide_ref
    return ref if ref and os.path.exists(ref) else None


def _first_image(scene: SceneIR) -> str | None:
    for ref in scene.visual_spec.image_refs:
        if ref and os.path.exists(ref):
            return ref
    return None


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _bundle_zip(
    zip_path: str,
    ir: CourseIR,
    video_path: str,
    srt_path: str,
    vtt_path: str,
    cover_path: str,
) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(zip_path)), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, arc in (
            (video_path, "video.mp4"),
            (srt_path, "subtitle.srt"),
            (vtt_path, "subtitle.vtt"),
            (cover_path, "cover.png"),
        ):
            if os.path.exists(src):
                zf.write(src, arcname=arc)
        zf.writestr("course_ir.json", ir.model_dump_json(indent=2))


def _to_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None
