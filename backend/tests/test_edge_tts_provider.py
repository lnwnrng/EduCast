"""Edge-TTS Provider 测试 — monkeypatch edge_tts，不发起真实网络调用。"""

from pathlib import Path

import edge_tts
import pytest

from app.providers.tts import get_tts_provider
from app.providers.tts.edge_tts_provider import EdgeTTSProvider


class _FakeCommunicate:
    """模拟 edge_tts.Communicate：save 写入假音频字节。"""

    last_args: tuple[str, str] = ("", "")
    last_rate: str = ""

    def __init__(self, text: str, voice: str, *, rate: str = "+0%") -> None:
        _FakeCommunicate.last_args = (text, voice)
        _FakeCommunicate.last_rate = rate

    async def save(self, path: str) -> None:
        Path(path).write_bytes(b"ID3\x03\x00fake-audio")


class _FailingCommunicate:
    def __init__(self, text: str, voice: str, *, rate: str = "+0%") -> None:
        pass

    async def save(self, path: str) -> None:
        raise RuntimeError("network down")


async def test_synthesize_writes_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(edge_tts, "Communicate", _FakeCommunicate)
    out = str(tmp_path / "nested" / "a.mp3")
    provider = EdgeTTSProvider(voice="zh-CN-XiaoxiaoNeural")

    result = await provider.synthesize("你好世界", out)

    assert result == out
    assert Path(out).exists()
    assert _FakeCommunicate.last_args == ("你好世界", "zh-CN-XiaoxiaoNeural")


async def test_submit_get_result_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(edge_tts, "Communicate", _FakeCommunicate)
    out = str(tmp_path / "b.mp3")
    provider = EdgeTTSProvider()

    task_id = await provider.submit({"text": "讲解内容", "output_path": out})
    result = await provider.get_result(task_id)

    assert result.status == "completed"
    assert result.result_url == out
    assert result.cost == 0.0
    assert Path(out).exists()


async def test_submit_propagates_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(edge_tts, "Communicate", _FailingCommunicate)
    provider = EdgeTTSProvider()
    with pytest.raises(RuntimeError):
        await provider.submit({"text": "x", "output_path": str(tmp_path / "c.mp3")})


async def test_get_result_unknown_task() -> None:
    provider = EdgeTTSProvider()
    result = await provider.get_result("nope")
    assert result.status == "failed"


async def test_synthesize_strips_markers_to_plain_text(
    tmp_path: Path, monkeypatch
) -> None:
    """含历史标记的讲稿 → 剥离为纯文本后传给 Edge-TTS（edge-tts 不支持 SSML）。"""
    monkeypatch.setattr(edge_tts, "Communicate", _FakeCommunicate)
    out = str(tmp_path / "marked.mp3")
    provider = EdgeTTSProvider(voice="zh-CN-XiaoxiaoNeural")

    await provider.synthesize("请看[PAUSE:0.5]这里是[EMPHASIS]重点[/EMPHASIS]", out)

    text_passed, voice_passed = _FakeCommunicate.last_args
    # 纯文本：无 SSML 标签、无方括号标记
    assert "<" not in text_passed
    assert "[PAUSE" not in text_passed and "[EMPHASIS]" not in text_passed
    assert text_passed == "请看这里是重点"
    assert voice_passed == "zh-CN-XiaoxiaoNeural"


async def test_synthesize_plain_text_unchanged(tmp_path: Path, monkeypatch) -> None:
    """无标记文本原样朗读，并带上全局语速参数。"""
    monkeypatch.setattr(edge_tts, "Communicate", _FakeCommunicate)
    out = str(tmp_path / "plain.mp3")
    provider = EdgeTTSProvider()

    await provider.synthesize("普通讲稿无标记", out)

    text_passed, _ = _FakeCommunicate.last_args
    assert text_passed == "普通讲稿无标记"
    # 语速参数透传（默认来自 settings.EDGE_TTS_RATE）
    assert _FakeCommunicate.last_rate.endswith("%")


def test_metadata_and_factory() -> None:
    provider = get_tts_provider()
    assert isinstance(provider, EdgeTTSProvider)
    assert provider.provider_name == "edge_tts"
    assert provider.estimate_cost({"text": "任意"}) == 0.0
