"""字幕/章节生成（纯函数）测试。"""

from app.pipeline.subtitles import (
    build_chapter_metadata,
    build_srt,
    build_vtt,
    format_timestamp,
)


def test_format_timestamp_srt_and_vtt() -> None:
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(1.5) == "00:00:01,500"
    assert format_timestamp(3661.234) == "01:01:01,234"
    # VTT 用点号分隔毫秒
    assert format_timestamp(1.5, vtt=True) == "00:00:01.500"
    # 负数被夹到 0
    assert format_timestamp(-3) == "00:00:00,000"


def test_build_srt_numbers_and_skips_empty() -> None:
    segments = [
        (0.0, 2.0, "第一句"),
        (2.0, 4.0, "   "),  # 空白 → 跳过
        (4.0, 6.5, "第三句"),
    ]
    srt = build_srt(segments)
    # 序号连续（空段被跳过后仍是 1、2）
    assert "1\n00:00:00,000 --> 00:00:02,000\n第一句" in srt
    assert "2\n00:00:04,000 --> 00:00:06,500\n第三句" in srt
    assert "第一句" in srt and "第三句" in srt
    assert srt.count("-->") == 2


def test_build_vtt_header() -> None:
    vtt = build_vtt([(0.0, 1.0, "你好")])
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.000" in vtt
    assert "你好" in vtt


def test_build_chapter_metadata() -> None:
    chapters = [
        (0.0, 12.0, "第一章 导数"),
        (12.0, 30.0, "第二章 积分"),
    ]
    meta = build_chapter_metadata(chapters)
    assert meta.startswith(";FFMETADATA1")
    assert meta.count("[CHAPTER]") == 2
    assert "TIMEBASE=1/1000" in meta
    assert "START=0" in meta
    assert "END=12000" in meta
    assert "START=12000" in meta
    assert "END=30000" in meta
    assert "title=第一章 导数" in meta


def test_build_chapter_metadata_escapes_special_chars() -> None:
    meta = build_chapter_metadata([(0.0, 1.0, "a=b;c#d")])
    assert "title=a\\=b\\;c\\#d" in meta
