"""字幕（SRT/VTT）与章节（FFmpeg metadata）生成 — 纯函数。

与 FFmpeg/IR 解耦：输入均为 ``(start, end, text)`` 秒级时间段元组，便于单元
测试。时间轴由 CompositionService 按各分镜旁白音频时长累计后传入。
"""

# (start_seconds, end_seconds, text)
Segment = tuple[float, float, str]


def format_timestamp(seconds: float, *, vtt: bool = False) -> str:
    """格式化为字幕时间戳。

    - SRT: ``HH:MM:SS,mmm``
    - VTT: ``HH:MM:SS.mmm``
    """
    total_ms = max(0, round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    sep = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def build_srt(segments: list[Segment]) -> str:
    """构建 SRT 字幕内容（跳过空文本段，序号连续）。"""
    blocks: list[str] = []
    index = 1
    for start, end, text in segments:
        text = (text or "").strip()
        if not text:
            continue
        blocks.append(
            f"{index}\n"
            f"{format_timestamp(start)} --> {format_timestamp(end)}\n"
            f"{text}\n"
        )
        index += 1
    return "\n".join(blocks)


def build_vtt(segments: list[Segment]) -> str:
    """构建 WebVTT 字幕内容。"""
    blocks: list[str] = ["WEBVTT\n"]
    for start, end, text in segments:
        text = (text or "").strip()
        if not text:
            continue
        blocks.append(
            f"{format_timestamp(start, vtt=True)} --> "
            f"{format_timestamp(end, vtt=True)}\n"
            f"{text}\n"
        )
    return "\n".join(blocks)


def _escape_metadata(value: str) -> str:
    """转义 FFmpeg metadata 值中的特殊字符（=、;、#、\\、换行）。"""
    out = []
    for ch in value:
        if ch in "=;#\\":
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\\n")
        else:
            out.append(ch)
    return "".join(out)


def build_chapter_metadata(chapters: list[Segment]) -> str:
    """构建 FFmpeg FFMETADATA 章节文件内容（时间基 1/1000，单位毫秒）。"""
    lines = [";FFMETADATA1", ""]
    for start, end, title in chapters:
        start_ms = max(0, round(start * 1000))
        end_ms = max(start_ms, round(end * 1000))
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={start_ms}")
        lines.append(f"END={end_ms}")
        lines.append(f"title={_escape_metadata((title or '').strip())}")
        lines.append("")
    return "\n".join(lines)
