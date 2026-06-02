"""课件渲染器 — 用 Pillow 把课件页/封面合成为视频底画面。

解析阶段并不产出真实幻灯片图片（只记录占位 ``slide_ref`` 与内嵌图
``image_refs``），因此底画面在这里由 IR 文本合成：标题 + 正文要点 + 可选内嵌图
+ 底部字幕条。P1 阶段非 slide 类型分镜（数字人/生成式/公式）同样降级为课件页
渲染——文本与角标用于区分画面意图。

设计：与 IR 解耦，``render_scene`` 接收已拆好的标题/正文/字幕等基本类型，由
CompositionService 负责从 ``SceneIR`` 映射，便于单元测试。
"""

import logging
import os

from PIL import Image, ImageDraw, ImageFont

from app.config import settings

logger = logging.getLogger(__name__)

# 候选 CJK 字体（按平台优先级）
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]


class SlideRenderer:
    """Pillow 课件渲染器。"""

    BG_COLOR = (248, 249, 251)
    HEADER_COLOR = (24, 38, 66)
    TITLE_COLOR = (24, 38, 66)
    BODY_COLOR = (45, 52, 64)
    ACCENT = (37, 99, 235)
    BADGE_BG = (37, 99, 235)
    BADGE_FG = (255, 255, 255)
    SUBTITLE_BG = (0, 0, 0, 165)
    SUBTITLE_FG = (255, 255, 255)
    WATERMARK_FG = (120, 120, 120, 130)

    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        font_path: str | None = None,
    ) -> None:
        self._w = width or settings.VIDEO_WIDTH
        self._h = height or settings.VIDEO_HEIGHT
        self._font_path = self._resolve_font(
            font_path if font_path is not None else settings.SLIDE_FONT_PATH
        )

    # ── 字体 ──────────────────────────────────────────────────

    @staticmethod
    def _resolve_font(font_path: str) -> str | None:
        if font_path and os.path.exists(font_path):
            return font_path
        for cand in _FONT_CANDIDATES:
            if os.path.exists(cand):
                return cand
        logger.warning("未找到 CJK 字体，回退 PIL 默认字体（中文可能显示为方块）")
        return None

    def _font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if self._font_path:
            try:
                return ImageFont.truetype(self._font_path, size)
            except OSError:
                logger.warning("加载字体失败: %s", self._font_path)
        return ImageFont.load_default()

    # ── 文本排版辅助 ──────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """把文本切成排版单元：ASCII 词整体、其余逐字符（适配中英混排换行）。"""
        units: list[str] = []
        buf = ""
        for ch in text:
            if ch.isascii() and (ch.isalnum() or ch in "_-./@"):
                buf += ch
            else:
                if buf:
                    units.append(buf)
                    buf = ""
                units.append(ch)
        if buf:
            units.append(buf)
        return units

    def _wrap(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        """按像素宽度换行，保留显式换行。"""
        lines: list[str] = []
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                continue
            cur = ""
            for unit in self._tokenize(paragraph):
                trial = cur + unit
                if not cur or draw.textlength(trial, font=font) <= max_width:
                    cur = trial
                else:
                    lines.append(cur.rstrip())
                    cur = unit if unit.strip() else ""
            if cur.strip():
                lines.append(cur.rstrip())
        return lines

    # ── 分镜渲染 ──────────────────────────────────────────────

    def render_scene(
        self,
        *,
        title: str,
        body_lines: list[str],
        subtitle: str = "",
        image_path: str | None = None,
        output_path: str,
        watermark: str | None = None,
        badge: str | None = None,
    ) -> str:
        """渲染单个分镜底画面为 PNG（1920×1080）。"""
        img = Image.new("RGBA", (self._w, self._h), (*self.BG_COLOR, 255))
        draw = ImageDraw.Draw(img)
        margin = int(self._w * 0.062)

        title_font = self._font(int(self._h * 0.056))
        body_font = self._font(int(self._h * 0.040))
        sub_font = self._font(int(self._h * 0.038))
        badge_font = self._font(int(self._h * 0.026))

        # 顶部标题 + 强调线
        title_y = int(self._h * 0.07)
        for line in self._wrap(draw, title or "", title_font, self._w - 2 * margin)[:2]:
            draw.text((margin, title_y), line, font=title_font, fill=self.TITLE_COLOR)
            title_y += int(self._h * 0.075)
        line_y = title_y + 6
        draw.rectangle(
            [margin, line_y, margin + int(self._w * 0.10), line_y + 6],
            fill=self.ACCENT,
        )

        # 角标（画面意图标签）
        if badge:
            bw = int(draw.textlength(badge, font=badge_font)) + 36
            bh = int(self._h * 0.05)
            bx = self._w - margin - bw
            draw.rounded_rectangle(
                [bx, int(self._h * 0.07), bx + bw, int(self._h * 0.07) + bh],
                radius=10,
                fill=self.BADGE_BG,
            )
            draw.text(
                (bx + 18, int(self._h * 0.07) + bh // 2 - badge_font.size // 2),
                badge,
                font=badge_font,
                fill=self.BADGE_FG,
            )

        # 正文区（可选右侧配图）
        body_top = line_y + int(self._h * 0.05)
        body_bottom = int(self._h * 0.78)
        body_right = self._w - margin
        if image_path and os.path.exists(image_path):
            try:
                photo = Image.open(image_path).convert("RGBA")
                box_w = int(self._w * 0.40)
                box_h = body_bottom - body_top
                photo.thumbnail((box_w, box_h))
                px = self._w - margin - photo.width
                py = body_top + (box_h - photo.height) // 2
                img.alpha_composite(photo, (px, py))
                body_right = px - int(self._w * 0.03)
            except Exception as exc:  # noqa: BLE001 — 配图失败不应中断渲染
                logger.warning("加载内嵌图失败 %s: %s", image_path, exc)

        # 正文要点（带强调圆点）
        y = body_top
        body_width = body_right - margin - int(self._w * 0.03)
        line_h = int(self._h * 0.06)
        for raw in body_lines:
            if y > body_bottom - line_h:
                break
            for wrapped in self._wrap(draw, raw, body_font, body_width):
                if y > body_bottom - line_h:
                    break
                dot_r = 7
                draw.ellipse(
                    [
                        margin,
                        y + body_font.size // 2 - dot_r,
                        margin + 2 * dot_r,
                        y + body_font.size // 2 + dot_r,
                    ],
                    fill=self.ACCENT,
                )
                draw.text(
                    (margin + int(self._w * 0.025), y),
                    wrapped,
                    font=body_font,
                    fill=self.BODY_COLOR,
                )
                y += line_h

        # 底部字幕条（半透明黑底 + 居中白字）
        if subtitle and subtitle.strip():
            self._draw_subtitle(img, draw, subtitle.strip(), sub_font, margin)

        # 水印
        if watermark:
            wm_font = self._font(int(self._h * 0.024))
            wm_w = int(draw.textlength(watermark, font=wm_font))
            draw.text(
                (self._w - margin - wm_w, int(self._h * 0.04)),
                watermark,
                font=wm_font,
                fill=self.WATERMARK_FG,
            )

        return self._save(img, output_path)

    def _draw_subtitle(
        self,
        img: Image.Image,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        margin: int,
    ) -> None:
        lines = self._wrap(draw, text, font, self._w - 4 * margin)[:3]
        line_h = int(font.size * 1.4)
        bar_h = line_h * len(lines) + int(self._h * 0.03)
        bar_top = self._h - bar_h - int(self._h * 0.03)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.rounded_rectangle(
            [margin, bar_top, self._w - margin, bar_top + bar_h],
            radius=18,
            fill=self.SUBTITLE_BG,
        )
        img.alpha_composite(overlay)

        y = bar_top + int(self._h * 0.015)
        for line in lines:
            lw = draw.textlength(line, font=font)
            draw.text(
                ((self._w - lw) / 2, y),
                line,
                font=font,
                fill=self.SUBTITLE_FG,
            )
            y += line_h

    # ── 封面 ──────────────────────────────────────────────────

    def render_cover(
        self,
        *,
        title: str,
        subject: str = "",
        grade: str = "",
        output_path: str,
    ) -> str:
        """渲染课程封面标题卡。"""
        img = Image.new("RGBA", (self._w, self._h), (*self.HEADER_COLOR, 255))
        draw = ImageDraw.Draw(img)
        margin = int(self._w * 0.08)

        title_font = self._font(int(self._h * 0.10))
        sub_font = self._font(int(self._h * 0.045))

        lines = self._wrap(draw, title or "教学视频", title_font, self._w - 2 * margin)
        total_h = len(lines) * int(self._h * 0.12)
        y = (self._h - total_h) // 2 - int(self._h * 0.05)
        for line in lines:
            lw = draw.textlength(line, font=title_font)
            draw.text(((self._w - lw) / 2, y), line, font=title_font, fill="white")
            y += int(self._h * 0.12)

        # 强调线
        draw.rectangle(
            [
                self._w // 2 - int(self._w * 0.08),
                y + 10,
                self._w // 2 + int(self._w * 0.08),
                y + 18,
            ],
            fill=self.ACCENT,
        )

        meta = " · ".join(p for p in (subject, grade) if p)
        if meta:
            mw = draw.textlength(meta, font=sub_font)
            draw.text(
                ((self._w - mw) / 2, y + int(self._h * 0.05)),
                meta,
                font=sub_font,
                fill=(200, 210, 230),
            )

        return self._save(img, output_path)

    # ── 公式动画（P3 占位）────────────────────────────────────

    def render_formula_animation(self, latex_steps: list[str], output_path: str) -> str:
        """渲染 LaTeX 公式推导动画。

        TODO(P3): 使用 manim 逐步显影。P1 阶段公式分镜降级为课件页渲染
        （由 CompositionService 调用 render_scene 把 latex_steps 当文本展示）。
        """
        logger.info(
            "公式动画占位(P3): %d 步 → %s",
            len(latex_steps),
            output_path,
        )
        body = [s for s in latex_steps if s.strip()] or ["（公式推导）"]
        return self.render_scene(
            title="公式推导",
            body_lines=body,
            badge="公式推导",
            output_path=output_path,
        )

    # ── 保存 ──────────────────────────────────────────────────

    @staticmethod
    def _save(img: Image.Image, output_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.convert("RGB").save(output_path)
        return output_path
