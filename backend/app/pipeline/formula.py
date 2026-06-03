"""公式推导动画渲染器（公式渲染画面）。

把 ``visual_spec.latex_steps`` 渲染为「逐步推导显影」视频：

- **manim 路径**（优先）：装好 manim + 系统 LaTeX(MiKTeX) 时，逐行 ``Write`` 推导步骤、
  关键步 ``Indicate`` 高亮，CPU 渲染，效果最佳。
- **图片显影路径**（自动降级，纯 pip）：用 matplotlib mathtext 把每一步渲染为 PNG，
  按「累计展示前 k 行、第 k 行高亮」拼出逐步显影视频；matplotlib 解析失败的步骤
  自动退化为纯文本。无需安装 LaTeX。

产物为**无声** mp4（旁白由合成层 ``video_audio_to_clip`` 叠加），时长由旁白驱动。
所有 ffmpeg 操作复用 ``app.utils.ffmpeg`` 原子助手，便于单测 monkeypatch。
"""

import importlib.util
import json
import logging
import os
import shutil
import subprocess

from app.config import settings
from app.utils import ffmpeg

logger = logging.getLogger(__name__)

# 深色板书风配色
_BG = "#0f1a2e"
_FG = "#e6ebf5"
_HL = "#4d9bff"

# 单步默认时长（无旁白驱动时）
_DEFAULT_STEP_SECONDS = 2.5


class FormulaRenderer:
    """LaTeX 公式逐步推导动画渲染器。"""

    def __init__(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
        engine: str | None = None,
    ) -> None:
        self._w = width or settings.VIDEO_WIDTH
        self._h = height or settings.VIDEO_HEIGHT
        self._fps = fps or settings.VIDEO_FPS
        self._engine = (engine or settings.FORMULA_ENGINE or "auto").lower()
        # 复用课件渲染器的 CJK 字体探测，供图片显影中的中文（标题/纯文本步骤）显示
        from app.pipeline.renderer import SlideRenderer

        self._cjk_font_path = SlideRenderer._resolve_font("")

    async def render(
        self,
        latex_steps: list[str],
        output_path: str,
        *,
        duration: float | None = None,
    ) -> str:
        """渲染公式推导动画为无声 mp4，返回路径。步骤为空抛 ValueError。"""
        steps = [s.strip() for s in latex_steps if s and s.strip()]
        if not steps:
            raise ValueError("公式步骤为空")

        engine = self._engine
        if engine == "auto":
            engine = "manim" if self._manim_available() else "image"

        if engine == "manim":
            try:
                return await self._render_manim(steps, output_path, duration)
            except Exception as exc:  # noqa: BLE001 — manim 失败自动降级图片显影
                logger.warning("manim 渲染失败，降级图片显影: %s", exc)

        return await self._render_image(steps, output_path, duration)

    # ── 能力探测 ──────────────────────────────────────────────

    @staticmethod
    def _manim_available() -> bool:
        """manim 已安装且系统 LaTeX 可用时才走 manim。"""
        if importlib.util.find_spec("manim") is None:
            return False
        return shutil.which("latex") is not None or shutil.which("xelatex") is not None

    def _step_seconds(self, steps: list[str], duration: float | None) -> float:
        if duration and duration > 0:
            return max(duration / len(steps), 1.0)
        return _DEFAULT_STEP_SECONDS

    # ── 图片显影路径（纯 pip 兜底）────────────────────────────

    async def _render_image(
        self, steps: list[str], output_path: str, duration: float | None
    ) -> str:
        per = self._step_seconds(steps, duration)
        workdir = f"{output_path}.steps"
        os.makedirs(workdir, exist_ok=True)
        clips: list[str] = []
        try:
            for k in range(1, len(steps) + 1):
                png = os.path.join(workdir, f"step_{k}.png")
                self._render_step_png(steps[:k], k - 1, png)
                clip = os.path.join(workdir, f"clip_{k}.mp4")
                await ffmpeg.image_audio_to_clip(
                    png,
                    None,
                    clip,
                    width=self._w,
                    height=self._h,
                    fps=self._fps,
                    duration=per,
                )
                clips.append(clip)
            await ffmpeg.concat_clips(clips, output_path)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        return output_path

    def _render_step_png(
        self, shown: list[str], highlight_index: int, output_path: str
    ) -> None:
        """渲染累计公式 PNG；mathtext 解析失败时退化为纯文本。"""
        try:
            self._draw_steps(shown, highlight_index, output_path, mathtext=True)
        except Exception as exc:  # noqa: BLE001 — 非法 mathtext → 纯文本兜底
            logger.warning("mathtext 渲染失败，退化纯文本: %s", exc)
            self._draw_steps(shown, highlight_index, output_path, mathtext=False)

    def _draw_steps(
        self,
        shown: list[str],
        highlight_index: int,
        output_path: str,
        *,
        mathtext: bool,
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.font_manager import FontProperties

        cjk = FontProperties(fname=self._cjk_font_path) if self._cjk_font_path else None

        fig = plt.figure(figsize=(self._w / 100, self._h / 100), dpi=100)
        fig.patch.set_facecolor(_BG)
        ax = fig.add_axes((0, 0, 1, 1))
        ax.axis("off")
        ax.set_facecolor(_BG)

        ax.text(
            0.1,
            0.9,
            "公式推导",
            color=_HL,
            fontsize=34,
            va="top",
            ha="left",
            fontproperties=cjk,
        )

        n = len(shown)
        top, bottom = 0.76, 0.12
        gap = (top - bottom) / max(n, 1)
        for i, step in enumerate(shown):
            y = top - i * gap - gap * 0.3
            is_hl = i == highlight_index
            color = _HL if is_hl else _FG
            size = 42 if is_hl else 34
            text = f"${step}$" if mathtext else step
            # 纯文本步骤用 CJK 字体；mathtext（$...$）由数学引擎渲染，多为 ASCII
            kw = {} if mathtext else {"fontproperties": cjk}
            ax.text(
                0.13, y, text, color=color, fontsize=size, va="top", ha="left", **kw
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        fig.savefig(output_path, facecolor=_BG, dpi=100)
        plt.close(fig)

    # ── manim 路径（可选，效果最佳）──────────────────────────

    async def _render_manim(
        self, steps: list[str], output_path: str, duration: float | None
    ) -> str:
        """生成临时 Scene 并以 manim CLI 渲染，产物拷回 output_path。"""
        per = self._step_seconds(steps, duration)
        workdir = f"{output_path}.manim"
        os.makedirs(workdir, exist_ok=True)
        scene_file = os.path.join(workdir, "scene.py")
        with open(scene_file, "w", encoding="utf-8") as f:
            f.write(_MANIM_TEMPLATE.format(steps=json.dumps(steps), run_time=per))

        cmd = [
            "manim",
            "render",
            "-qm",
            "--format",
            "mp4",
            "--fps",
            str(self._fps),
            "--resolution",
            f"{self._w},{self._h}",
            "--media_dir",
            workdir,
            scene_file,
            "FormulaScene",
        ]

        def _exec() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )

        import asyncio

        try:
            await asyncio.to_thread(_exec)
            produced = _find_mp4(workdir)
            if produced is None:
                raise RuntimeError("manim 未产出 mp4")
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            shutil.copyfile(produced, output_path)
            return output_path
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


def _find_mp4(root: str) -> str | None:
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(".mp4"):
                return os.path.join(dirpath, name)
    return None


_MANIM_TEMPLATE = """\
import json
from manim import *

STEPS = json.loads({steps!r})
RUN_TIME = {run_time}


class FormulaScene(Scene):
    def construct(self):
        self.camera.background_color = "#0f1a2e"
        prev = None
        for step in STEPS:
            try:
                eq = MathTex(step, color=WHITE)
            except Exception:
                eq = Text(step, color=WHITE, font_size=36)
            eq.scale(1.0)
            if prev is None:
                eq.to_edge(UP).shift(DOWN * 1.2)
            else:
                eq.next_to(prev, DOWN, buff=0.45)
            self.play(Write(eq), run_time=max(RUN_TIME * 0.6, 0.6))
            self.play(Indicate(eq, color="#4d9bff"), run_time=max(RUN_TIME * 0.4, 0.4))
            prev = eq
        self.wait(0.5)
"""
