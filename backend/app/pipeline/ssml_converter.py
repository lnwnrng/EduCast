"""将讲稿中的语音标记转换为 Edge-TTS 兼容的 SSML。

标记语法（由 LLM 脚本编排阶段插入）:
- [PAUSE:0.8]                 → <break time="800ms"/>
- [EMPHASIS]重点内容[/EMPHASIS] → <prosody rate="92%" pitch="+3%">重点内容</prosody>
- [SLOW]缓讲内容[/SLOW]        → <prosody rate="80%">缓讲内容</prosody>

设计:
- ``narration_to_ssml`` 将带标记文本包裹为完整 SSML 文档。
- ``strip_markers`` 移除所有标记，返回纯文本（用于字幕）。
- 两个函数均为纯函数，无副作用，便于单测。
"""

import re

# ── 标记正则 ──────────────────────────────────────────────

_PAUSE_RE = re.compile(r"\[PAUSE:([\d.]+)\]")
_EMPHASIS_OPEN = re.compile(r"\[EMPHASIS\]")
_EMPHASIS_CLOSE = re.compile(r"\[/EMPHASIS\]")
_SLOW_OPEN = re.compile(r"\[SLOW\]")
_SLOW_CLOSE = re.compile(r"\[/SLOW\]")

# 匹配所有标记（用于检测和剥离）
_ALL_MARKERS = re.compile(r"\[PAUSE:[\d.]+\]" r"|(?:\[/?EMPHASIS\])" r"|(?:\[/?SLOW\])")


def narration_to_ssml(
    text: str,
    voice: str = "zh-CN-XiaoxiaoNeural",
) -> str:
    """将带语音标记的讲稿文本转换为 Edge-TTS 兼容 SSML。

    Args:
        text: 含 [PAUSE:N] / [EMPHASIS]...[/EMPHASIS] / [SLOW]...[/SLOW] 标记的文本。
        voice: Edge-TTS 语音名称。

    Returns:
        完整的 SSML XML 字符串。若输入无标记则返回最简 SSML 包裹。
    """
    if not text or not text.strip():
        return ""

    inner = text

    # [PAUSE:0.8] → <break time="800ms"/>
    inner = _PAUSE_RE.sub(
        lambda m: f'<break time="{int(float(m.group(1)) * 1000)}ms"/>',
        inner,
    )

    # [EMPHASIS]...[/EMPHASIS] → <prosody rate="92%" pitch="+3%">...</prosody>
    inner = _EMPHASIS_OPEN.sub('<prosody rate="92%" pitch="+3%">', inner)
    inner = _EMPHASIS_CLOSE.sub("</prosody>", inner)

    # [SLOW]...[/SLOW] → <prosody rate="80%">...</prosody>
    inner = _SLOW_OPEN.sub('<prosody rate="80%">', inner)
    inner = _SLOW_CLOSE.sub("</prosody>", inner)

    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xml:lang="zh-CN">'
        f'<voice name="{voice}">{inner}</voice>'
        "</speak>"
    )


def has_markers(text: str) -> bool:
    """检测文本中是否包含语音标记。"""
    return bool(_ALL_MARKERS.search(text or ""))


def strip_markers(text: str) -> str:
    """移除所有语音标记，返回纯文本（用于字幕生成）。"""
    return _ALL_MARKERS.sub("", text or "").strip()
