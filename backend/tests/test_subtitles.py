"""字幕/章节生成（纯函数）测试。"""

from app.pipeline.subtitles import (
    build_chapter_metadata,
    build_narration_segments,
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


def test_build_narration_segments_splits_long_narration() -> None:
    text = (
        "我们先从平均变化率出发，理解导数的几何含义。"
        "接着观察割线逐渐靠近切线的过程，说明极限为什么能描述瞬时变化率。"
        "最后把这个思想写成导数定义。"
    )
    segments = build_narration_segments([(0.0, 9.0, text)])

    assert len(segments) > 1
    assert segments[0][0] == 0.0
    assert segments[-1][1] == 9.0
    assert all(
        end <= next_start
        for (_, end, _), (next_start, _, _) in zip(segments, segments[1:])
    )
    assert all(len(cue) <= 56 for _, _, cue in segments)
    assert "导数定义" in segments[-1][2]


def test_build_narration_segments_uses_only_non_empty_narration() -> None:
    segments = build_narration_segments(
        [
            (0.0, 3.0, ""),
            (3.0, 6.0, "第一句。第二句。"),
        ]
    )

    assert [
        (round(start, 3), round(end, 3), text) for start, end, text in segments
    ] == [
        (3.0, 4.5, "第一句。"),
        (4.5, 6.0, "第二句。"),
    ]


def test_build_narration_segments_merges_when_scene_is_short() -> None:
    segments = build_narration_segments([(0.0, 1.0, "第一句。第二句。第三句。")])

    assert segments == [(0.0, 1.0, "第一句。第二句。第三句。")]


def test_visible_len_counts_cjk_as_two() -> None:
    from app.pipeline.subtitles import _visible_len

    # 汉字算 2 宽度，ASCII 算 1
    assert _visible_len("导数") == 4
    assert _visible_len("ab") == 2
    assert _visible_len("导ab") == 4  # 2 + 1 + 1


def test_build_segments_caps_cjk_width() -> None:
    """CJK 宽度感知：单 cue 不超过 22 宽度单位（≈11 汉字）。"""
    long_cjk = "我们一起来理解导数的几何含义及其在瞬时变化率中的应用。" * 2
    segments = build_narration_segments([(0.0, 20.0, long_cjk)])
    assert len(segments) > 1
    from app.pipeline.subtitles import _visible_len

    # 合并后单 cue 也不超过 max_chars*2 = 44 宽度（合并阈值）
    assert all(_visible_len(cue) <= 44 for _, _, cue in segments)
    assert segments[0][0] == 0.0
    assert segments[-1][1] == 20.0
