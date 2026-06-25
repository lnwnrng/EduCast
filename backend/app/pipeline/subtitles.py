"""字幕（SRT/VTT）与章节（FFmpeg metadata）生成 — 纯函数。

与 FFmpeg/IR 解耦：输入均为 ``(start, end, text)`` 秒级时间段元组，便于单元
测试。时间轴由 CompositionService 按各分镜旁白音频时长累计后传入。
"""

import re
import unicodedata

# (start_seconds, end_seconds, text)
Segment = tuple[float, float, str]

_PRIMARY_SPLIT_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?", re.MULTILINE)
_SOFT_SPLIT_RE = re.compile(r"[^，、：:,]+[，、：:,]?", re.MULTILINE)

# 字幕单 cue 最大「可视宽度」：CJK 字符算 2 宽度，ASCII 算 1。
# 22 宽度 ≈ 11 个汉字或 22 个字母，视觉上单行舒适不溢出。
DEFAULT_MAX_CUE_CHARS = 22
DEFAULT_MIN_CUE_SECONDS = 1.2


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


def build_narration_segments(
    scene_segments: list[Segment],
    *,
    max_chars: int = DEFAULT_MAX_CUE_CHARS,
    min_seconds: float = DEFAULT_MIN_CUE_SECONDS,
) -> list[Segment]:
    """把分镜级旁白切成电影式短字幕 cue。

    输入仍是分镜级 ``(start, end, narration_text)``；输出是更细的字幕 cue。
    同一分镜内按文本长度比例分配时间，保证首尾时间与分镜对齐。
    """
    out: list[Segment] = []
    for start, end, text in scene_segments:
        text = _collapse_spaces(text)
        if not text or end <= start:
            continue

        chunks = _merge_short_cues(
            _split_narration(text, max_chars=max_chars),
            duration=end - start,
            max_chars=max_chars,
            min_seconds=min_seconds,
        )
        if not chunks:
            continue

        out.extend(_allocate_times(start, end, chunks))
    return out


def _split_narration(text: str, *, max_chars: int) -> list[str]:
    """按自然停顿优先切分旁白文本。"""
    chunks: list[str] = []
    for sentence in _regex_chunks(_PRIMARY_SPLIT_RE, text):
        if _visible_len(sentence) <= max_chars:
            chunks.append(sentence)
            continue
        chunks.extend(_split_long_sentence(sentence, max_chars=max_chars))
    return chunks


def _split_long_sentence(text: str, *, max_chars: int) -> list[str]:
    """长句先按软停顿切，再按字符上限兜底。"""
    chunks: list[str] = []
    for part in _regex_chunks(_SOFT_SPLIT_RE, text):
        if _visible_len(part) <= max_chars:
            chunks.append(part)
            continue
        chunks.extend(_split_by_length(part, max_chars=max_chars))
    return chunks


def _merge_short_cues(
    chunks: list[str],
    *,
    duration: float,
    max_chars: int,
    min_seconds: float,
) -> list[str]:
    """分镜太短时合并相邻短 cue，避免字幕闪烁。"""
    chunks = [c for c in chunks if c.strip()]
    if len(chunks) <= 1:
        return chunks

    max_cues = max(1, int(duration / min_seconds))
    if len(chunks) <= max_cues:
        return chunks

    merged: list[str] = []
    current = ""
    for chunk in chunks:
        trial = _join_chunks(current, chunk) if current else chunk
        if current and _visible_len(trial) > max_chars * 2:
            merged.append(current)
            current = chunk
        else:
            current = trial
    if current:
        merged.append(current)

    while len(merged) > max_cues and len(merged) > 1:
        best_idx = min(
            range(len(merged) - 1),
            key=lambda i: _visible_len(merged[i]) + _visible_len(merged[i + 1]),
        )
        merged[best_idx] = _join_chunks(merged[best_idx], merged.pop(best_idx + 1))
    return merged


def _allocate_times(start: float, end: float, chunks: list[str]) -> list[Segment]:
    """按 cue 文本长度比例分配分镜内时间。"""
    if len(chunks) == 1:
        return [(start, end, chunks[0])]

    duration = end - start
    weights = [max(_visible_len(c), 1) for c in chunks]
    total = sum(weights)
    cursor = start
    segments: list[Segment] = []
    for i, chunk in enumerate(chunks):
        cue_end = (
            end if i == len(chunks) - 1 else cursor + duration * weights[i] / total
        )
        segments.append((cursor, cue_end, chunk))
        cursor = cue_end
    return segments


def _regex_chunks(pattern: re.Pattern[str], text: str) -> list[str]:
    chunks = [_collapse_spaces(m.group(0)) for m in pattern.finditer(text)]
    chunks = [c for c in chunks if c]
    return chunks or [_collapse_spaces(text)]


def _split_by_length(text: str, *, max_chars: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for ch in text:
        if not current and ch.isspace():
            continue
        if _visible_len(current + ch) > max_chars:
            chunks.append(current.strip())
            current = ch.lstrip()
        else:
            current += ch
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _join_chunks(left: str, right: str) -> str:
    """合并 cue 文本；英文/数字相邻时保留一个空格。"""
    left = left.strip()
    right = right.strip()
    if not left:
        return right
    if not right:
        return left
    if left[-1].isascii() and right[0].isascii():
        return f"{left} {right}"
    return f"{left}{right}"


def _visible_len(text: str) -> int:
    """CJK 宽度感知的「可视长度」：汉字/全角字符算 2，其余算 1。

    用于字幕 cue 宽度限制，避免一行汉字过多溢出屏幕。
    """
    text = (text or "").strip()
    width = 0
    for ch in text:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("W", "F") else 1
    return width


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
