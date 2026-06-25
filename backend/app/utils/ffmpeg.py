"""FFmpeg 命令构建与执行工具。

提供两类能力：
- ``FFmpegCommand``：Builder 模式构建单输入滤镜命令（水印/字幕硬嵌等）。
- 模块级合成助手（``probe_duration`` / ``image_audio_to_clip`` /
  ``concat_clips`` / ``mux_subtitle_and_chapters``）：模块三逐镜合成所需的
  原子操作。全部经单一 ``_run`` 执行，便于单元测试 monkeypatch，避免对真实
  FFmpeg 的依赖。
"""

import asyncio
import logging
import os
import subprocess

from app.config import settings

logger = logging.getLogger(__name__)


class FFmpegCommand:
    """FFmpeg 命令构建器 — Builder 模式。

    使用示例:
        cmd = (
            FFmpegCommand()
            .add_input("background.mp4")
            .add_input("narrator.mp3")
            .set_codec()
            .set_resolution()
            .add_subtitle("subtitles.srt")
            .set_output("output.mp4")
        )
        output_path = await cmd.run()
    """

    def __init__(self) -> None:
        self._inputs: list[str] = []
        self._filters: list[str] = []
        self._output: str | None = None
        self._video_codec: str = "libx264"
        self._audio_codec: str = "aac"
        self._audio_bitrate: str = "128k"
        self._preset: str = "medium"
        self._width: int = 1920
        self._height: int = 1080
        self._fps: int = 30
        self._extra_args: list[str] = []

    def add_input(self, path: str) -> "FFmpegCommand":
        """添加输入文件。"""
        self._inputs.append(path)
        return self

    def set_output(self, path: str) -> "FFmpegCommand":
        """设置输出文件路径。"""
        self._output = path
        return self

    def add_filter(self, filter_str: str) -> "FFmpegCommand":
        """添加视频滤镜。"""
        self._filters.append(filter_str)
        return self

    def add_subtitle(self, srt_path: str) -> "FFmpegCommand":
        """添加字幕叠加。"""
        self._filters.append(f"subtitles={srt_path}")
        return self

    def add_watermark(
        self,
        image_path: str,
        position: str = "10:10",
    ) -> "FFmpegCommand":
        """添加水印。"""
        self._filters.append(f"movie={image_path}[wm];[in][wm]overlay={position}")
        return self

    def set_codec(
        self,
        video: str = "libx264",
        audio: str = "aac",
    ) -> "FFmpegCommand":
        """设置编解码器。"""
        self._video_codec = video
        self._audio_codec = audio
        return self

    def set_resolution(self, width: int = 1920, height: int = 1080) -> "FFmpegCommand":
        """设置输出分辨率。"""
        self._width = width
        self._height = height
        return self

    def build(self) -> list[str]:
        """构建 FFmpeg 命令参数列表。"""
        if not self._output:
            raise ValueError("必须设置输出文件路径")

        cmd = ["ffmpeg", "-y"]

        # 输入
        for inp in self._inputs:
            cmd.extend(["-i", inp])

        # 滤镜
        if self._filters:
            cmd.extend(["-vf", ",".join(self._filters)])

        # 编码
        cmd.extend(
            [
                "-c:v",
                self._video_codec,
                "-preset",
                self._preset,
                "-c:a",
                self._audio_codec,
                "-b:a",
                self._audio_bitrate,
                "-r",
                str(self._fps),
                "-s",
                f"{self._width}x{self._height}",
            ]
        )

        # 额外参数
        cmd.extend(self._extra_args)

        # 输出
        cmd.append(self._output)

        return cmd

    async def run(self) -> str:
        """异步执行 FFmpeg 命令，返回输出路径。"""
        cmd = self.build()
        logger.info("执行 FFmpeg: %s", " ".join(cmd))

        def _run() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

        try:
            await asyncio.to_thread(_run)
            logger.info("FFmpeg 执行成功: %s", self._output)
            return self._output  # type: ignore[return-value]
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg 执行失败: %s", exc.stderr)
            raise


# ── 模块级合成助手 ───────────────────────────────────────────
#
# 这些函数是模块三逐镜合成的原子操作。它们是仅有的真正调用外部
# ffmpeg/ffprobe 二进制的地方；上层（VideoComposer / CompositionService）
# 通过它们间接合成，单元测试可对本模块函数做 monkeypatch 以脱离真实 FFmpeg。


async def _run(args: list[str]) -> str:
    """执行外部命令，返回 stdout（失败抛 CalledProcessError）。"""
    logger.info("执行: %s", " ".join(args))

    def _exec() -> subprocess.CompletedProcess[str]:
        # 显式 UTF-8 解码：ffmpeg 横幅含非本地编码字节，Windows 默认 gbk 会报错
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

    proc = await asyncio.to_thread(_exec)
    return proc.stdout


async def probe_duration(path: str) -> float:
    """用 ffprobe 读取媒体时长（秒）；失败或无法解析时返回 0.0。"""
    try:
        out = await _run(
            [
                settings.FFPROBE_BIN,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ]
        )
        return float(out.strip())
    except (subprocess.CalledProcessError, ValueError) as exc:
        logger.warning("ffprobe 读取时长失败 (%s): %s", path, exc)
        return 0.0


async def image_audio_to_clip(
    image_path: str,
    audio_path: str | None,
    output_path: str,
    *,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    duration: float | None = None,
) -> str:
    """由静态图（+可选旁白音频）生成单分镜 MP4。

    始终编码为统一参数（libx264/yuv420p + aac 128k + 指定 WxH/fps），并保证
    含一条音频流，以便后续用 concat demuxer 无损拼接。

    - 有 ``audio_path``：时长 = 音频时长（``-shortest``）。
    - 无音频：用 ``anullsrc`` 生成静音轨，时长取 ``duration``（兜底 4 秒）。
    """
    vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
    vf += f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1"

    args = [settings.FFMPEG_BIN, "-y", "-loop", "1", "-i", image_path]

    if audio_path:
        args += ["-i", audio_path]
        tail = ["-shortest"]
    else:
        args += [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
        ]
        tail = ["-t", str(duration if duration and duration > 0 else 4.0)]

    args += [
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        *tail,
        output_path,
    ]
    await _run(args)
    return output_path


# 画中画尺寸 → 前景宽度占成片宽度的比例（small/medium/large）
_PIP_WIDTH_FRAC: dict[str, float] = {"small": 0.22, "medium": 0.30, "large": 0.40}


def _audio_input(audio_path: str | None) -> tuple[list[str], str]:
    """构造音频输入参数与其流标识。

    有 ``audio_path`` 用之；否则用 ``anullsrc`` 生成静音轨。返回 (输入参数, map 标识)。
    调用方需保证音频是最后一个输入（标识里的索引由 ``input_index`` 决定）。
    """
    if audio_path:
        return ["-i", audio_path], "a"
    return (
        ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"],
        "a",
    )


def _venc_tail(fps: int, output_path: str, *, duration: float) -> list[str]:
    """统一的视频/音频编码尾参（与 image_audio_to_clip 同规格，便于 concat 拼接）。"""
    return [
        "-t",
        str(duration if duration and duration > 0 else settings.SILENT_SCENE_DURATION),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        output_path,
    ]


async def video_audio_to_clip(
    video_path: str,
    audio_path: str | None,
    output_path: str,
    *,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    duration: float,
) -> str:
    """把一段已有视频（生成式片段/公式动画/数字人）归一化为标准单镜 MP4。

    源视频缩放铺满 WxH（保比例 + 黑边），按 ``duration`` 截断；不足时循环补足
    （``-stream_loop -1``）。音频取 ``audio_path``（旁白），无则静音轨。便于后续
    concat demuxer 与课件页片段无损拼接。
    """
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps}"
    )
    args = [settings.FFMPEG_BIN, "-y", "-stream_loop", "-1", "-i", video_path]
    audio_args, _ = _audio_input(audio_path)
    args += audio_args
    args += ["-vf", vf, "-map", "0:v", "-map", "1:a"]
    args += _venc_tail(fps, output_path, duration=duration)
    await _run(args)
    return output_path


async def image_to_kenburns_clip(
    image_path: str,
    audio_path: str | None,
    output_path: str,
    *,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    duration: float,
) -> str:
    """由静态图做 Ken-Burns 缓慢推近运镜，生成有动感的单镜 MP4。

    用于「生成式片段」无 API/失败时的兜底——让概念底图也有镜头语言。预放大后
    ``zoompan`` 缓慢推进，避免抖动。
    """
    secs = duration if duration and duration > 0 else settings.SILENT_SCENE_DURATION
    frames = max(int(round(secs * fps)), 1)
    vf = (
        f"scale={width * 2}:-2,"
        f"zoompan=z='min(zoom+0.0010,1.20)':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps},"
        f"setsar=1"
    )
    args = [settings.FFMPEG_BIN, "-y", "-loop", "1", "-i", image_path]
    audio_args, _ = _audio_input(audio_path)
    args += audio_args
    args += ["-vf", vf, "-map", "0:v", "-map", "1:a"]
    args += _venc_tail(fps, output_path, duration=secs)
    await _run(args)
    return output_path


async def overlay_pip_clip(
    background_path: str,
    foreground_path: str,
    audio_path: str | None,
    output_path: str,
    *,
    position: str = "bottom_right",
    size: str = "small",
    fg_is_video: bool = False,
    float_motion: bool = True,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    duration: float,
) -> str:
    """把讲师前景（头像图 / 云端口播视频）以画中画叠加到课件底图上。

    用于「数字人」分镜：背景=课件页，前景按 ``size`` 缩放、按 ``position`` 定位
    （四角/全屏）。前景为静态图时加轻微上下浮动制造「在讲」的动感（``float_motion``）。
    音频取旁白，时长由 ``duration`` 决定。
    """
    secs = duration if duration and duration > 0 else settings.SILENT_SCENE_DURATION
    margin = int(round(min(width, height) * 0.04))

    args = [settings.FFMPEG_BIN, "-y", "-loop", "1", "-i", background_path]
    if fg_is_video:
        args += ["-stream_loop", "-1", "-i", foreground_path]
    else:
        args += ["-loop", "1", "-i", foreground_path]
    audio_args, _ = _audio_input(audio_path)
    args += audio_args  # 第三个输入 → 索引 2

    bg_chain = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1,fps={fps}[bg]"
    )

    if position == "full_screen":
        fg_chain = (
            f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}[fg]"
        )
        x_expr, y_expr = "0", "0"
    else:
        fg_w = int(round(width * _PIP_WIDTH_FRAC.get(size, 0.22)))
        fg_chain = f"[1:v]scale={fg_w}:-1[fg]"
        if position == "bottom_left":
            x_expr, y_base = str(margin), f"H-h-{margin}"
        elif position == "top_right":
            x_expr, y_base = f"W-w-{margin}", str(margin)
        elif position == "top_left":
            x_expr, y_base = str(margin), str(margin)
        else:  # bottom_right（默认）
            x_expr, y_base = f"W-w-{margin}", f"H-h-{margin}"
        y_expr = (
            f"{y_base}-8*sin(2*PI*t/3)" if float_motion and not fg_is_video else y_base
        )

    overlay = f"[bg][fg]overlay=x={x_expr}:y={y_expr}:format=auto[v]"
    filter_complex = ";".join([bg_chain, fg_chain, overlay])

    args += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "2:a"]
    args += _venc_tail(fps, output_path, duration=secs)
    await _run(args)
    return output_path


async def concat_clips(
    clip_paths: list[str], output_path: str, *, faststart: bool = False
) -> str:
    """用 concat demuxer 无损拼接多个同参数 MP4 片段。

    ``faststart=True`` 时把 moov 原子前置（仅当 concat 结果即最终成片、不再二次
    封装时需要），保证浏览器可流式播放/拖动进度。
    """
    if not clip_paths:
        raise ValueError("没有可拼接的片段")

    list_path = f"{output_path}.concat.txt"
    lines = []
    for p in clip_paths:
        # concat 列表用单引号包裹路径；统一正斜杠，转义内部单引号
        safe = os.path.abspath(p).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{safe}'")
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    args = [
        settings.FFMPEG_BIN,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
        "-c",
        "copy",
    ]
    if faststart:
        args += ["-movflags", "+faststart"]
    args.append(output_path)

    try:
        await _run(args)
    finally:
        if os.path.exists(list_path):
            os.remove(list_path)
    return output_path


async def mux_subtitle_and_chapters(
    video_path: str,
    output_path: str,
    *,
    srt_path: str | None = None,
    chapter_metadata_path: str | None = None,
) -> str:
    """为成片复用软字幕（mov_text）与章节 metadata（均为可选）。"""
    args = [settings.FFMPEG_BIN, "-y", "-i", video_path]

    # 输入索引：0=视频；按需追加 章节metadata / 字幕
    meta_idx: int | None = None
    sub_idx: int | None = None
    next_idx = 1
    if chapter_metadata_path:
        args += ["-f", "ffmetadata", "-i", chapter_metadata_path]
        meta_idx = next_idx
        next_idx += 1
    if srt_path:
        args += ["-i", srt_path]
        sub_idx = next_idx
        next_idx += 1

    args += ["-map", "0"]
    if sub_idx is not None:
        args += ["-map", str(sub_idx)]
    args += ["-map_metadata", str(meta_idx) if meta_idx is not None else "0"]
    args += ["-c", "copy"]
    if sub_idx is not None:
        args += ["-c:s", "mov_text"]
    # moov 前置：这是最终成片步骤，保证浏览器可流式播放/拖动进度
    args += ["-movflags", "+faststart"]
    args += [output_path]

    await _run(args)
    return output_path


# ── 视觉增强：转场 / 片头 / 片尾 ────────────────────────────
#
# 以下函数为核心工作流重设计新增，提升视频动感与专业度。

# CJK 字体候选（与 renderer.py 保持一致）
_CJK_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]

# xfade 转场名称映射（IR TransitionType → FFmpeg xfade 名称）
_XFADE_MAP: dict[str, str] = {
    "fade": "fade",
    "dissolve": "dissolve",
    "slide_left": "slideleft",
    "slide_right": "slideright",
    "cut": "fade",  # cut 用极短 fade 模拟
}


def _find_cjk_font() -> str | None:
    """查找系统可用的 CJK 字体路径。"""
    font_path = getattr(settings, "SLIDE_FONT_PATH", "")
    if font_path and os.path.exists(font_path):
        return font_path
    for cand in _CJK_FONT_CANDIDATES:
        if os.path.exists(cand):
            return cand
    return None


def _escape_drawtext(text: str) -> str:
    """转义 FFmpeg drawtext 滤镜中的特殊字符。"""
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\u2019")
        .replace(":", "\\:")
        .replace("%", "%%")
    )


async def concat_with_transitions(
    clip_paths: list[str],
    output_path: str,
    transitions: list[str] | None = None,
    transition_duration: float = 0.5,
    *,
    faststart: bool = True,
) -> str:
    """使用 xfade 滤镜链拼接分镜片段并加入转场效果。

    当 transitions 为 None 或所有转场为 'cut' 时，退化为普通 concat。
    FFmpeg xfade 支持: fade / dissolve / slideleft / slideright 等。

    Args:
        clip_paths: 各分镜片段路径列表。
        output_path: 输出成片路径。
        transitions: 转场类型列表（长度 = len(clip_paths) - 1）。
                     支持: 'fade' / 'dissolve' / 'slide_left' / 'slide_right' / 'cut'。
        transition_duration: 转场时长（秒），默认 0.5。
        faststart: 是否前置 moov 原子。
    """
    if not clip_paths:
        raise ValueError("没有可拼接的片段")

    if len(clip_paths) == 1:
        # 单片段直接复制
        args = [settings.FFMPEG_BIN, "-y", "-i", clip_paths[0], "-c", "copy"]
        if faststart:
            args += ["-movflags", "+faststart"]
        args.append(output_path)
        await _run(args)
        return output_path

    # 无转场或全 cut → 退化为普通拼接
    if not transitions or all(t == "cut" for t in transitions):
        return await concat_clips(clip_paths, output_path, faststart=faststart)

    # 补齐 transitions 列表长度
    n = len(clip_paths) - 1
    trans = list(transitions[:n])
    while len(trans) < n:
        trans.append("fade")

    # 探测每个片段时长
    durations: list[float] = []
    for p in clip_paths:
        d = await probe_duration(p)
        durations.append(d if d > 0 else 4.0)

    # 构建 xfade 滤镜链
    # [0:v][1:v]xfade=transition=fade:duration=0.5:offset=T0[v01];
    # [v01][2:v]xfade=transition=dissolve:duration=0.5:offset=T1[v012]; ...
    args = [settings.FFMPEG_BIN, "-y"]
    for p in clip_paths:
        args += ["-i", p]

    filters_v: list[str] = []
    filters_a: list[str] = []
    offset = 0.0

    for i in range(n):
        xfade_name = _XFADE_MAP.get(trans[i], "fade")
        dur = transition_duration if trans[i] != "cut" else 0.05

        if i == 0:
            src_label = "[0:v]"
        else:
            src_label = f"[v{i}]"
        next_label = f"[{i + 1}:v]"

        if i < n - 1:
            out_label = f"[v{i + 1}]"
        else:
            out_label = "[vout]"

        offset = sum(durations[: i + 1]) - (i + 1) * dur
        offset = max(offset, 0)

        filters_v.append(
            f"{src_label}{next_label}xfade=transition={xfade_name}"
            f":duration={dur:.3f}:offset={offset:.3f}{out_label}"
        )

        # 音频交叉淡化
        if i == 0:
            a_src = "[0:a]"
        else:
            a_src = f"[a{i}]"
        a_next = f"[{i + 1}:a]"
        if i < n - 1:
            a_out = f"[a{i + 1}]"
        else:
            a_out = "[aout]"
        filters_a.append(
            f"{a_src}{a_next}acrossfade=d={dur:.3f}:c1=tri:c2=tri{a_out}"
        )

    filter_complex = ";".join(filters_v + filters_a)
    args += [
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
    ]
    if faststart:
        args += ["-movflags", "+faststart"]
    args.append(output_path)

    await _run(args)
    return output_path


async def generate_intro_clip(
    output_path: str,
    *,
    title: str,
    subject: str = "",
    template_colors: tuple[int, int, int] = (24, 38, 66),
    duration: float = 4.0,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> str:
    """生成动态片头：纯色背景 + 标题渐显 + 学科信息渐显。

    使用 FFmpeg color + drawtext + fade 滤镜实现，无需外部图片资源。
    """
    r, g, b = template_colors
    hex_color = f"{r:02x}{g:02x}{b:02x}"

    font_path = _find_cjk_font()
    font_arg = f":fontfile='{font_path.replace(os.sep, '/')}'" if font_path else ""

    escaped_title = _escape_drawtext(title or "教学视频")
    escaped_subject = _escape_drawtext(subject) if subject else ""

    # 标题：在 0.6s 时开始淡入，持续 0.8s
    title_alpha = "alpha='if(lt(t\\,0.6)\\,0\\,if(lt(t\\,1.4)\\,(t-0.6)/0.8\\,1))'"
    title_filter = (
        f"drawtext=text='{escaped_title}'{font_arg}"
        f":fontsize=72:fontcolor=white:{title_alpha}"
        f":x=(w-tw)/2:y=(h-th)/2-40"
    )

    filters = [title_filter]

    # 学科信息：在 1.5s 时开始淡入
    if escaped_subject:
        sub_alpha = "alpha='if(lt(t\\,1.5)\\,0\\,if(lt(t\\,2.3)\\,(t-1.5)/0.8\\,1))'"
        sub_filter = (
            f"drawtext=text='{escaped_subject}'{font_arg}"
            f":fontsize=36:fontcolor=white@0.8:{sub_alpha}"
            f":x=(w-tw)/2:y=(h/2)+50"
        )
        filters.append(sub_filter)

    # 课影品牌标：在底部
    brand_alpha = "alpha='if(lt(t\\,2.0)\\,0\\,if(lt(t\\,2.8)\\,(t-2.0)/0.8\\,1))'"
    brand_filter = (
        f"drawtext=text='课影 EduCast'{font_arg}"
        f":fontsize=24:fontcolor=white@0.5:{brand_alpha}"
        f":x=(w-tw)/2:y=h-60"
    )
    filters.append(brand_filter)

    vf = ",".join(filters)

    args = [
        settings.FFMPEG_BIN,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x{hex_color}:s={width}x{height}:d={duration}:r={fps}",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf",
        vf,
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        output_path,
    ]
    await _run(args)
    return output_path


async def generate_outro_clip(
    output_path: str,
    *,
    title: str,
    summary_text: str = "感谢观看",
    template_colors: tuple[int, int, int] = (24, 38, 66),
    duration: float = 3.0,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> str:
    """生成片尾总结卡：纯色背景 + 课程标题 + 感谢文字 + 渐隐。"""
    r, g, b = template_colors
    hex_color = f"{r:02x}{g:02x}{b:02x}"

    font_path = _find_cjk_font()
    font_arg = f":fontfile='{font_path.replace(os.sep, '/')}'" if font_path else ""

    escaped_title = _escape_drawtext(title or "教学视频")
    escaped_summary = _escape_drawtext(summary_text)

    # 全程显示标题，最后 0.8s 淡出
    fade_out = duration - 0.8
    title_alpha = (
        f"alpha='if(lt(t\\,{fade_out:.1f})\\,1\\,"
        f"1-(t-{fade_out:.1f})/0.8)'"
    )
    title_filter = (
        f"drawtext=text='{escaped_title}'{font_arg}"
        f":fontsize=56:fontcolor=white:{title_alpha}"
        f":x=(w-tw)/2:y=(h-th)/2-30"
    )

    summary_alpha = (
        f"alpha='if(lt(t\\,{fade_out:.1f})\\,1\\,"
        f"1-(t-{fade_out:.1f})/0.8)'"
    )
    summary_filter = (
        f"drawtext=text='{escaped_summary}'{font_arg}"
        f":fontsize=36:fontcolor=white@0.7:{summary_alpha}"
        f":x=(w-tw)/2:y=(h/2)+40"
    )

    vf = f"{title_filter},{summary_filter}"

    args = [
        settings.FFMPEG_BIN,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x{hex_color}:s={width}x{height}:d={duration}:r={fps}",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf",
        vf,
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        output_path,
    ]
    await _run(args)
    return output_path

