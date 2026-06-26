"""讲稿语音标记的剥离工具。

历史上脚本编排会在讲稿中插入 [PAUSE:N] / [EMPHASIS]…[/EMPHASIS] / [SLOW]…[/SLOW]
等内联标记并试图转成 SSML 喂给 Edge-TTS。但 edge-tts 不支持 SSML 输入（会对整段做
XML 转义、把标签当文字念出来），导致配音逐字朗读 XML、与字幕完全对不上。

现在编排不再生成这些标记、TTS 直接朗读纯文本。本模块仅保留 ``strip_markers``
作为**防御性清理**：兼容历史 IR 或模型偶发输出的残留标记（字幕生成、TTS 入参、
合成页正文兜底均会先剥离）。纯函数，无副作用，便于单测。
"""

import re

# 匹配所有历史语音标记（用于剥离）
_ALL_MARKERS = re.compile(r"\[PAUSE:[\d.]+\]" r"|(?:\[/?EMPHASIS\])" r"|(?:\[/?SLOW\])")


def strip_markers(text: str) -> str:
    """移除所有历史语音标记，返回纯文本。无标记时原样返回（仅去首尾空白）。"""
    return _ALL_MARKERS.sub("", text or "").strip()
