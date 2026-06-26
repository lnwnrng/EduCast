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

import asyncio
import json
import logging
import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ir.schema import CourseIR, KnowledgePointIR, SceneIR, SceneType
from app.models.project import Project
from app.models.resource import Resource
from app.models.task import SubTask, Task
from app.pipeline.composer import VideoComposer
from app.pipeline.formula import FormulaRenderer
from app.pipeline.progress import DEFAULT_STEP_DETAIL, band_progress
from app.pipeline.renderer import SlideRenderer
from app.pipeline.ssml_converter import strip_markers
from app.pipeline.subtitles import (
    build_chapter_metadata,
    build_narration_segments,
    build_srt,
    build_vtt,
)
from app.pipeline.templates import get_template
from app.providers.digital_human import (
    LocalDigitalHumanProvider,
    get_digital_human_provider,
)
from app.providers.tts import get_tts_provider
from app.providers.video_gen import get_video_gen_provider
from app.services.parser_service import ParserService
from app.services.resource_service import ResourceService
from app.utils import ffmpeg
from app.utils.hash import compute_input_hash
from app.utils.task_helpers import to_uuid as _to_uuid
from app.utils.task_helpers import update_task_status

# 区分"构造参数未传入"与"显式传入 None（用于关闭某能力）"
_UNSET = object()

logger = logging.getLogger(__name__)

_BADGES: dict[SceneType, str | None] = {
    SceneType.SLIDE: None,
    SceneType.FORMULA_ANIMATION: "公式推导",
    SceneType.DIGITAL_HUMAN: "讲解",
    SceneType.GENERATIVE_CLIP: "概念演示",
}

_SENTENCE_SPLIT = re.compile(r"[。！？!?\n]+")


def _card_text(value: object, max_len: int) -> str:
    """把 Outline 文案规整为片头/片尾卡片单行文本（折叠空白 + 截断）。"""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len].rstrip() + "…"


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


@dataclass
class _Visual:
    """单镜画面资产（渲染产物，待与旁白合成）。

    ``_render_*_asset`` 只负责产出资产并记失败 subtask；成功 subtask 由
    ``_build_scene_clip`` 在 ``_mux_visual`` 成功后补记（与原串行实现语义一致）。
    """

    mux: str  # "static" | "kenburns" | "video_audio" | "overlay_pip"
    image: str | None = None  # static / kenburns / overlay_pip 的底图
    video: str | None = None  # video_audio 的源视频
    fg: str | None = None  # overlay_pip 的前景
    fg_is_video: bool = False
    pip_position: str = "bottom_right"
    pip_size: str = "small"
    # 成功后由调用方补记的 subtask 信息
    subtask_pending: bool = False  # True=需补记成功 subtask（slide 已自记，False）
    subtask_type: str = "render"
    subtask_url: str | None = None  # None → 用 clip_path
    provider: str | None = None


class CompositionService:
    """教学视频合成编排服务。"""

    def __init__(
        self,
        *,
        tts_provider=None,
        renderer: SlideRenderer | None = None,
        composer: VideoComposer | None = None,
        formula_renderer: FormulaRenderer | None = None,
        video_gen_provider=_UNSET,
        digital_human_provider=_UNSET,
        digital_human_local=None,
    ) -> None:
        self._parser_service = ParserService()
        self._tts = tts_provider if tts_provider is not None else get_tts_provider()
        self._renderer = renderer or SlideRenderer()
        self._composer = composer or VideoComposer()
        # 并行（TTS ‖ 渲染）时串行化 DB flush——async session 不可重入，
        # 并发 db.add/flush 会损坏状态；锁只护 flush，不阻塞 I/O。
        self._db_lock = asyncio.Lock()
        self._formula = formula_renderer or FormulaRenderer()
        # 云端视频生成（CogVideoX）；无 Key → None → Ken-Burns 兜底
        self._video_gen = (
            get_video_gen_provider()
            if video_gen_provider is _UNSET
            else video_gen_provider
        )
        # 云端数字人（本轮 None）+ 本地讲师兜底
        self._dh_cloud = (
            get_digital_human_provider()
            if digital_human_provider is _UNSET
            else digital_human_provider
        )
        self._dh_local = digital_human_local or LocalDigitalHumanProvider()

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
                db,
                task_id,
                "failed",
                None,
                step_detail=DEFAULT_STEP_DETAIL["failed"],
                error_message="合成失败：未找到 IR",
            )
            await self._update_project(db, project_id, "failed")
            return

        flat = _flatten(ir)

        # 根据 IR 模板配置创建渲染器（覆盖默认配色）
        self._renderer = SlideRenderer(template_name=ir.template or "micro_lecture")
        if not flat:
            await self._update_task(
                db,
                task_id,
                "failed",
                None,
                step_detail=DEFAULT_STEP_DETAIL["failed"],
                error_message="合成失败：IR 无分镜",
            )
            await self._update_project(db, project_id, "failed")
            return

        try:
            # generating 区间起点 = 45（reviewing 检查点之后继续，不回退到 50）
            await self._update_task(
                db,
                task_id,
                "generating",
                band_progress("generating", 0, 1),
                step_detail=DEFAULT_STEP_DETAIL["generating"],
            )
            await self._update_project(db, project_id, "generating")

            # 生成版本号（按现有视频数递增）与生成配置（音色 / 能力开关）
            gen = await self._next_gen_version(db, project_id)
            cfg = self._task_config(await db.get(Task, _to_uuid(task_id)))
            voice = str(cfg["tts_voice"]) if cfg.get("tts_voice") else None
            use_generative = bool(cfg.get("use_generative", False))
            use_digital_human = bool(cfg.get("use_digital_human", True))
            use_watermark = bool(cfg.get("use_watermark", True))
            use_ai_full_gen = bool(cfg.get("use_ai_full_gen", False))

            root = settings.STORAGE_ROOT
            workspace = os.path.join(root, project_id, "workspace", task_id)
            output_dir = os.path.join(root, project_id, "output")
            export_dir = os.path.join(root, project_id, "export")
            os.makedirs(workspace, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(export_dir, exist_ok=True)

            watermark = settings.WATERMARK_TEXT or ir.title or "课影 EduCast"
            task_uuid = _to_uuid(task_id)

            # ── 视觉增强开关 ──
            use_transitions = bool(settings.VIDEO_TRANSITIONS)
            use_intro_outro = bool(settings.VIDEO_INTRO_OUTRO)
            td = settings.TRANSITION_DURATION if use_transitions else 0.0
            tpl = get_template(ir.template or "micro_lecture")
            cover_bg = tpl.colors.cover_bg

            # 片头/片尾文案复用 Outline 产出（opening_hook / closing_summary），
            # 不再写死「感谢观看」；缺失时回退到学科 / 默认致谢。
            outline = ir.teaching_outline or {}
            intro_subtitle = _card_text(outline.get("opening_hook"), 28) or (
                ir.subject or ""
            )
            outro_summary = _card_text(outline.get("closing_summary"), 40) or "感谢观看"

            # ── 片头（可选）──
            intro_path: str | None = None
            intro_dur = 0.0
            if use_intro_outro:
                intro_path = os.path.join(workspace, "intro.mp4")
                try:
                    await ffmpeg.generate_intro_clip(
                        intro_path,
                        title=ir.title or "教学视频",
                        subject=intro_subtitle,
                        template_colors=cover_bg,
                        duration=settings.INTRO_DURATION,
                        width=settings.VIDEO_WIDTH,
                        height=settings.VIDEO_HEIGHT,
                        fps=settings.VIDEO_FPS,
                    )
                    intro_dur = settings.INTRO_DURATION
                except Exception as exc:  # noqa: BLE001 — 片头失败不阻断出片
                    logger.warning("片头生成失败，跳过: %s", exc)
                    intro_path = None
                    intro_dur = 0.0

            # ── 片尾（可选）──
            outro_path: str | None = None
            if use_intro_outro:
                outro_path = os.path.join(workspace, "outro.mp4")
                try:
                    await ffmpeg.generate_outro_clip(
                        outro_path,
                        title=ir.title or "教学视频",
                        summary_text=outro_summary,
                        template_colors=cover_bg,
                        duration=settings.OUTRO_DURATION,
                        width=settings.VIDEO_WIDTH,
                        height=settings.VIDEO_HEIGHT,
                        fps=settings.VIDEO_FPS,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("片尾生成失败，跳过: %s", exc)
                    outro_path = None

            # ── 逐分镜：渲染 + 配音 + 单镜片段 ──
            # 时间轴补偿：转场 (xfade) 会让相邻分镜音频重叠 td，故每镜起点前移 td；
            # 字幕终点在转场开始处截断，避免与下一镜字幕重叠。片头占 [0, intro_dur]，
            # 若同时启用转场，首镜与片头重叠 td。
            clip_paths: list[str] = []
            scene_transitions: list[str] = []
            cursor = intro_dur
            if use_transitions and intro_path:
                cursor = max(cursor - td, 0.0)
            total = len(flat)
            for i, fs in enumerate(flat):
                clip = await self._build_scene_clip(
                    db,
                    task_uuid,
                    fs,
                    i,
                    workspace,
                    watermark,
                    voice=voice,
                    use_generative=use_generative,
                    use_digital_human=use_digital_human,
                    use_ai_full_gen=use_ai_full_gen,
                )
                if clip is None:
                    continue
                clip_path, duration = clip
                full_end = cursor + duration
                has_next = (i < total - 1) or bool(outro_path)
                cut = td if (use_transitions and has_next) else 0.0
                fs.start = cursor
                fs.end = full_end - cut
                # 下一镜音频起点（转场重叠 td）
                cursor = full_end - (td if (use_transitions and i < total - 1) else 0.0)
                clip_paths.append(clip_path)
                scene_transitions.append(fs.scene.transition.value)

                await self._update_task(
                    db,
                    task_id,
                    "generating",
                    band_progress("generating", i + 1, total),
                    step_detail=f"生成第 {i + 1}/{total} 个分镜素材…",
                )

            if not clip_paths:
                raise RuntimeError("所有分镜片段生成失败")

            # ── 字幕 / 章节 ──
            await self._update_task(
                db,
                task_id,
                "composing",
                band_progress("composing", 1, 3),
                step_detail="生成字幕与章节…",
            )
            # 字幕用纯文本（剥离 SSML 标记），时间轴已按转场补偿
            segments = build_narration_segments(
                [
                    (fs.start, fs.end, strip_markers(fs.scene.narration_text))
                    for fs in flat
                    if fs.scene.narration_text.strip()
                ]
            )
            chapters = _chapter_spans(flat)

            srt_path = os.path.join(output_dir, f"gen{gen}.srt")
            vtt_path = os.path.join(output_dir, f"gen{gen}.vtt")
            chapter_path = os.path.join(workspace, "chapters.txt")
            _write(srt_path, build_srt(segments))
            _write(vtt_path, build_vtt(segments))
            _write(chapter_path, build_chapter_metadata(chapters))

            # ── FFmpeg 合成 ──
            video_path = os.path.join(output_dir, f"gen{gen}.mp4")
            # 转场列表 = 分镜间转场（长度 = len(clip_paths)-1）；片头/片尾的 fade
            # 由 VideoComposer 自动补齐
            transitions = (
                scene_transitions[: max(len(clip_paths) - 1, 0)]
                if use_transitions
                else None
            )
            await self._composer.compose(
                clip_paths,
                video_path,
                srt_path=srt_path,
                chapter_metadata_path=chapter_path,
                transitions=transitions,
                intro_path=intro_path,
                outro_path=outro_path,
                transition_duration=settings.TRANSITION_DURATION,
            )

            # ── 视频级水印（文字 drawtext）──
            if use_watermark:
                wm_text = settings.WATERMARK_TEXT or ir.title or "课影 EduCast"
                wm_watermarked = os.path.join(output_dir, f"gen{gen}_wm.mp4")
                try:
                    from app.utils.ffmpeg import FFmpegCommand

                    cmd = FFmpegCommand()
                    cmd.add_input(video_path)
                    escaped = wm_text.replace("'", "\u2019").replace(":", "\\:")
                    cmd.add_filter(
                        f"drawtext=text='{escaped}'"
                        ":fontsize=28:fontcolor=white@0.35"
                        ":x=w-tw-30:y=h-th-20"
                    )
                    cmd.set_output(wm_watermarked)
                    await cmd.run()
                    if (
                        os.path.exists(wm_watermarked)
                        and os.path.getsize(wm_watermarked) > 0
                    ):
                        os.replace(wm_watermarked, video_path)
                        logger.info("视频水印已添加")
                    else:
                        logger.warning("水印生成失败，使用无水印版本")
                except Exception:
                    logger.warning("添加水印失败，使用无水印版本", exc_info=True)

            # ── 封面 ──
            cover_path = os.path.join(output_dir, f"gen{gen}_cover.png")
            await asyncio.to_thread(
                self._renderer.render_cover,
                title=ir.title or "教学视频",
                subject=ir.subject,
                grade=ir.grade,
                output_path=cover_path,
            )

            # ── zip 打包 ──
            await self._update_task(
                db,
                task_id,
                "composing",
                band_progress("composing", 2, 3),
                step_detail="打包导出资源…",
            )
            zip_path = os.path.join(export_dir, f"gen{gen}.zip")
            _bundle_zip(zip_path, ir, video_path, srt_path, vtt_path, cover_path)

            # ── 入库 ──
            await self._register_resources(
                db,
                project_id,
                ir,
                gen,
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
                step_detail=DEFAULT_STEP_DETAIL["completed"],
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
                db,
                task_id,
                "failed",
                None,
                step_detail=DEFAULT_STEP_DETAIL["failed"],
                error_message=f"合成失败: {exc}",
            )
            await self._update_project(db, project_id, "failed")

    # ── 单分镜片段（按画面类型分发）────────────────────────────

    async def _build_scene_clip(
        self,
        db: AsyncSession,
        task_uuid: UUID | None,
        fs: _FlatScene,
        index: int,
        workspace: str,
        watermark: str,
        *,
        voice: str | None = None,
        use_generative: bool = False,
        use_digital_human: bool = True,
        use_ai_full_gen: bool = False,
    ) -> tuple[str, float] | None:
        """配音 + 按 scene_type 生成单镜片段，返回 (片段路径, 时长)。失败返回 None。

        **TTS 与画面渲染并行**：旁白合成（网络 I/O）与画面资产渲染（CPU/网络）
        无依赖，用 ``asyncio.gather`` 并行执行以提速；两者仅在 DB subtask 写入时
        经 ``self._db_lock`` 串行化 flush。合成（mux）需音频+画面就绪后执行。

        公式/数字人/生成式各有专用画面，任一失败均降级为课件页静图，保证出片。
        """
        scene = fs.scene
        clip_path = os.path.join(workspace, f"clip_{index}.mp4")

        # ── 并行：TTS（含 tts subtask）‖ 画面资产渲染 ──
        audio_task = asyncio.create_task(
            self._narration_audio(db, task_uuid, scene, index, workspace, voice)
        )

        st = scene.scene_type
        visual: _Visual | None = None
        try:
            if use_ai_full_gen:
                # AI 全生成模式：忽略 scene_type，所有画面走 CogVideoX
                visual = await self._render_gen_asset(
                    db,
                    task_uuid,
                    fs,
                    index,
                    workspace,
                    watermark,
                    clip_path,
                    use_generative=True,
                    ai_auto_prompt=True,
                )
            elif st == SceneType.FORMULA_ANIMATION:
                visual = await self._render_formula_asset(
                    db, task_uuid, scene, index, workspace, clip_path
                )
            elif st == SceneType.DIGITAL_HUMAN and use_digital_human:
                visual = await self._render_dh_asset(
                    db, task_uuid, fs, index, workspace, watermark, clip_path
                )
            elif st == SceneType.GENERATIVE_CLIP:
                visual = await self._render_gen_asset(
                    db,
                    task_uuid,
                    fs,
                    index,
                    workspace,
                    watermark,
                    clip_path,
                    use_generative=use_generative,
                )
            else:
                # slide 主路径（与 TTS 并行渲染）
                visual = await self._render_slide_asset(
                    db, task_uuid, fs, index, workspace, watermark
                )
        except Exception as exc:  # noqa: BLE001 — 专用画面异常 → 课件页兜底
            logger.warning("分镜 %d 专用画面渲染失败，降级课件页: %s", index, exc)
            visual = None

        # 等音频就绪（若渲染先完成，此处即等待 TTS）
        audio_path, duration = await audio_task

        # 主画面未就绪 → 课件页兜底（此时音频已就绪，串行渲染）
        if visual is None:
            visual = await self._render_slide_asset(
                db, task_uuid, fs, index, workspace, watermark
            )
        if visual is None:
            return None

        # 合成（需音频 + 画面）
        try:
            built = await self._mux_visual(visual, audio_path, duration, clip_path)
        except Exception as exc:  # noqa: BLE001 — mux 失败则跳过该镜
            logger.warning("分镜 %d 片段合成失败，跳过: %s", index, exc)
            built = False

        if built and visual.subtask_pending:
            await self._add_subtask(
                db,
                task_uuid,
                visual.subtask_type,
                scene.scene_id,
                "completed",
                visual.subtask_url or clip_path,
                provider=visual.provider,
            )
        return (clip_path, duration) if built else None

    async def _mux_visual(
        self,
        visual: _Visual,
        audio_path: str | None,
        duration: float,
        clip_path: str,
    ) -> bool:
        """按画面类型把资产与旁白合成为单镜片段。"""
        if visual.mux == "static":
            # 真实课件页静止展示（像正常投影），不做运镜
            await ffmpeg.image_audio_to_clip(
                visual.image,
                audio_path,
                clip_path,
                width=settings.VIDEO_WIDTH,
                height=settings.VIDEO_HEIGHT,
                fps=settings.VIDEO_FPS,
                duration=duration,
            )
        elif visual.mux == "kenburns":
            await ffmpeg.image_to_kenburns_clip(
                visual.image,
                audio_path,
                clip_path,
                width=settings.VIDEO_WIDTH,
                height=settings.VIDEO_HEIGHT,
                fps=settings.VIDEO_FPS,
                duration=duration,
            )
        elif visual.mux == "video_audio":
            await ffmpeg.video_audio_to_clip(
                visual.video,
                audio_path,
                clip_path,
                width=settings.VIDEO_WIDTH,
                height=settings.VIDEO_HEIGHT,
                fps=settings.VIDEO_FPS,
                duration=duration,
            )
        elif visual.mux == "overlay_pip":
            await ffmpeg.overlay_pip_clip(
                visual.image,
                visual.fg,
                audio_path,
                clip_path,
                position=visual.pip_position,
                size=visual.pip_size,
                fg_is_video=visual.fg_is_video,
                width=settings.VIDEO_WIDTH,
                height=settings.VIDEO_HEIGHT,
                fps=settings.VIDEO_FPS,
                duration=duration,
            )
        else:
            return False
        return True

    async def _narration_audio(
        self,
        db: AsyncSession,
        task_uuid: UUID | None,
        scene: SceneIR,
        index: int,
        workspace: str,
        voice: str | None,
    ) -> tuple[str | None, float]:
        """逐镜配音（无旁白/失败 → 静音降级），返回 (音频路径|None, 时长)。"""
        narration = (scene.narration_text or "").strip()
        audio_path = os.path.join(workspace, f"scene_{index}.mp3")
        used_audio: str | None = None
        if narration:
            try:
                await self._tts.synthesize(narration, audio_path, voice=voice)
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

        duration = 0.0
        if used_audio:
            duration = await ffmpeg.probe_duration(used_audio)
        if duration <= 0:
            duration = settings.SILENT_SCENE_DURATION
        return used_audio, duration

    async def _render_slide_asset(
        self,
        db: AsyncSession,
        task_uuid: UUID | None,
        fs: _FlatScene,
        index: int,
        workspace: str,
        watermark: str,
    ) -> _Visual | None:
        """渲染课件页静图。成功记 render subtask。

        真实课件页（已栅格化的 PPT/PDF 页图）默认**静止展示**——它们本就是排好版
        的成品，平移推近只会让文字游移、显得「无意义运镜」。仅对文本合成页 / 纯图片
        画面保留轻微 Ken-Burns 运镜，避免呆板。可用 ``KEN_BURNS_REAL_SLIDES`` 覆盖。
        """
        scene = fs.scene
        image_path = os.path.join(workspace, f"scene_{index}.png")
        try:
            await asyncio.to_thread(
                self._renderer.render_scene,
                title=fs.kp.title or "教学内容",
                body_lines=_body_lines(scene, fs.kp),
                subtitle="",
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
        # 真实课件页静止；合成/图片画面保留轻微运镜
        is_real_slide = _real_slide(scene) is not None
        static = is_real_slide and not settings.KEN_BURNS_REAL_SLIDES
        return _Visual(mux="static" if static else "kenburns", image=image_path)

    async def _render_formula_asset(
        self,
        db: AsyncSession,
        task_uuid: UUID | None,
        scene: SceneIR,
        index: int,
        workspace: str,
        clip_path: str,
    ) -> _Visual | None:
        """渲染公式推导动画视频。无步骤返回 None（不记 subtask）；失败记 failed。

        成功 subtask 由 ``_build_scene_clip`` 在 mux 后补记（result_url=clip_path）。
        """
        steps = [s for s in scene.visual_spec.latex_steps if s and s.strip()]
        if not steps:
            return None
        try:
            formula_video = os.path.join(workspace, f"formula_{index}.mp4")
            # 时长由旁白驱动，渲染时用占位时长；mux 阶段会用真实 duration 对齐
            await self._formula.render(steps, formula_video)
            return _Visual(
                mux="video_audio",
                video=formula_video,
                subtask_pending=True,
                subtask_type="formula",
                subtask_url=clip_path,
                provider="formula",
            )
        except Exception as exc:  # noqa: BLE001 — 公式动画失败 → 课件页兜底
            logger.warning("分镜 %d 公式动画失败，降级课件页: %s", index, exc)
            await self._add_subtask(
                db, task_uuid, "formula", scene.scene_id, "failed", error=str(exc)
            )
            return None

    async def _render_dh_asset(
        self,
        db: AsyncSession,
        task_uuid: UUID | None,
        fs: _FlatScene,
        index: int,
        workspace: str,
        watermark: str,
        clip_path: str,
    ) -> _Visual | None:
        """渲染讲师画中画资产：课件底图 + 讲师前景（云端视频 / 本地头像）。

        成功 subtask 由 ``_build_scene_clip`` 在 mux 后补记。
        """
        scene = fs.scene
        try:
            bg = os.path.join(workspace, f"dh_bg_{index}.png")
            await asyncio.to_thread(
                self._renderer.render_scene,
                title=fs.kp.title or "教学内容",
                body_lines=_body_lines(scene, fs.kp),
                subtitle="",
                output_path=bg,
                watermark=watermark,
                badge=_BADGES.get(scene.scene_type),
                background_path=_real_slide(scene),
            )
            if self._dh_cloud is not None:
                # 真机云数字人（接入后）：取回口播视频作前景
                fg = os.path.join(workspace, f"dh_fg_{index}.mp4")
                await self._dh_cloud.generate(
                    prompt=scene.narration_text, output_path=fg
                )
                fg_is_video = True
                provider_name = self._dh_cloud.provider_name
            else:
                # 本地兜底：静态讲师头像前景
                fg = os.path.join(workspace, f"dh_fg_{index}.png")
                await self._dh_local.render_foreground(fg)
                fg_is_video = False
                provider_name = self._dh_local.provider_name

            return _Visual(
                mux="overlay_pip",
                image=bg,
                fg=fg,
                fg_is_video=fg_is_video,
                pip_position=scene.visual_spec.pip_position.value,
                pip_size=scene.visual_spec.pip_size.value,
                subtask_pending=True,
                subtask_type="digital_human",
                subtask_url=clip_path,
                provider=provider_name,
            )
        except Exception as exc:  # noqa: BLE001 — 数字人失败 → 课件页兜底
            logger.warning("分镜 %d 数字人失败，降级课件页: %s", index, exc)
            await self._add_subtask(
                db,
                task_uuid,
                "digital_human",
                scene.scene_id,
                "failed",
                error=str(exc),
            )
            return None

    async def _render_gen_asset(
        self,
        db: AsyncSession,
        task_uuid: UUID | None,
        fs: _FlatScene,
        index: int,
        workspace: str,
        watermark: str,
        clip_path: str,
        *,
        use_generative: bool,
        ai_auto_prompt: bool = False,
    ) -> _Visual | None:
        """渲染生成式片段资产：CogVideoX 真生成（带缓存）；否则概念图。

        成功 subtask 由 ``_build_scene_clip`` 在 mux 后补记。
        """
        scene = fs.scene
        prompt = (scene.visual_spec.gen_prompt or "").strip()
        # AI 全生成模式下，若 gen_prompt 为空，自动从旁白生成提示词
        if not prompt and ai_auto_prompt:
            narration = (scene.narration_text or "").strip()
            kp_title = fs.kp.title or ""
            prompt = (
                f"教学场景：{kp_title}。{narration[:80]}"
                if narration
                else f"教学场景：{kp_title}"
            )
        if not prompt:
            return None
        try:
            if use_generative and self._video_gen is not None:
                generated = await self._generate_or_cache(prompt)
                return _Visual(
                    mux="video_audio",
                    video=generated,
                    subtask_pending=True,
                    subtask_type="video_gen",
                    subtask_url=generated,
                    provider=self._video_gen.provider_name,
                )
            # 兜底：概念底图（Ken-Burns 运镜在 mux 阶段应用）
            bg = os.path.join(workspace, f"gen_bg_{index}.png")
            await asyncio.to_thread(
                self._renderer.render_scene,
                title=fs.kp.title or "概念演示",
                body_lines=[f"画面：{prompt}"],
                subtitle="",
                output_path=bg,
                watermark=watermark,
                badge=_BADGES.get(scene.scene_type),
                background_path=_real_slide(scene),
            )
            return _Visual(
                mux="kenburns",
                image=bg,
                subtask_pending=True,
                subtask_type="video_gen",
                subtask_url=clip_path,
                provider="kenburns_fallback",
            )
        except Exception as exc:  # noqa: BLE001 — 生成式失败 → 课件页兜底
            logger.warning("分镜 %d 生成式片段失败，降级课件页: %s", index, exc)
            await self._add_subtask(
                db, task_uuid, "video_gen", scene.scene_id, "failed", error=str(exc)
            )
            return None

    async def _generate_or_cache(self, prompt: str) -> str:
        """生成式片段缓存：相同 (模型, 提示词) 命中复用，避免重复付费。"""
        key = compute_input_hash(f"{settings.COGVIDEO_MODEL}|{prompt}")
        cache_dir = os.path.join(settings.STORAGE_ROOT, "_cache", "video_gen")
        cached = os.path.join(cache_dir, f"{key}.mp4")
        if os.path.exists(cached):
            logger.info("生成式片段命中缓存: %s", cached)
            return cached
        os.makedirs(cache_dir, exist_ok=True)
        await self._video_gen.generate(prompt, cached)
        return cached

    # ── 入库 ──────────────────────────────────────────────────

    async def _register_resources(
        self,
        db: AsyncSession,
        project_id: str,
        ir: CourseIR,
        gen: int,
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
        v = gen
        await ResourceService.create_resource(
            db,
            pid,
            "video",
            f"{ir.title} 成片 第{v}版",
            video_path,
            mime_type="video/mp4",
            version=v,
            watermark_applied=True,
            metadata={
                "subject": ir.subject,
                "grade": ir.grade,
                "ir_version": ir.version,
            },
        )
        await ResourceService.create_resource(
            db,
            pid,
            "subtitle",
            f"{ir.title} 字幕 SRT 第{v}版",
            srt_path,
            mime_type="application/x-subrip",
            version=v,
        )
        await ResourceService.create_resource(
            db,
            pid,
            "subtitle",
            f"{ir.title} 字幕 VTT 第{v}版",
            vtt_path,
            mime_type="text/vtt",
            version=v,
        )
        await ResourceService.create_resource(
            db,
            pid,
            "image",
            f"{ir.title} 封面 第{v}版",
            cover_path,
            mime_type="image/png",
            version=v,
        )
        await ResourceService.create_resource(
            db,
            pid,
            "archive",
            f"{ir.title} 打包 第{v}版",
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
        # 并行场景下（TTS ‖ 渲染）serialize flush，避免 async session 重入损坏
        async with self._db_lock:
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
        progress: int | None = None,
        step_detail: str | None = None,
        ir_snapshot_path: str | None = None,
        error_message: str | None = None,
        actual_cost: float | None = None,
    ) -> None:
        """更新任务状态（委托给共享 update_task_status —— 含 WebSocket 广播）。

        改为委托后，生成/合成阶段（45–98%）也会实时广播进度与 step_detail，
        前端 WS 不再只在解析/编排阶段收到推送。
        """
        await update_task_status(
            db,
            task_id,
            status,
            progress,
            step_detail=step_detail,
            ir_snapshot_path=ir_snapshot_path,
            error_message=error_message,
            actual_cost=actual_cost,
        )

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

    async def _next_gen_version(self, db: AsyncSession, project_id: str) -> int:
        """下一个成片版本号 = 该项目现有视频资源数 + 1（每次生成独立成版）。"""
        pid = _to_uuid(project_id)
        if pid is None:
            return 1
        stmt = select(func.count(Resource.id)).where(
            Resource.project_id == pid,
            Resource.resource_type == "video",
            Resource.is_folder.is_(False),
            Resource.deleted_at.is_(None),
        )
        return int((await db.execute(stmt)).scalar() or 0) + 1

    @staticmethod
    def _task_config(task: Task | None) -> dict:
        """解析任务 config_json（音色 / 能力开关等生成参数）。"""
        if task is None or not task.config_json:
            return {}
        try:
            cfg = json.loads(task.config_json)
        except (ValueError, TypeError):
            return {}
        return cfg if isinstance(cfg, dict) else {}

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
    text = strip_markers(scene.narration_text or scene.subtitle_text)
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
