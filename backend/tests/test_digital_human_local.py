"""数字人本地兜底测试 — 头像渲染（透明底）+ Provider 工厂。"""

from PIL import Image

from app.pipeline.renderer import SlideRenderer
from app.providers.digital_human import (
    LocalDigitalHumanProvider,
    get_digital_human_provider,
)


def test_render_avatar_produces_rgba_png(tmp_path) -> None:
    out = tmp_path / "avatar.png"
    SlideRenderer().render_avatar(name="王老师", output_path=str(out))
    assert out.exists()
    img = Image.open(out)
    assert img.mode == "RGBA"  # 透明底以便画中画叠加
    # 四角应当透明（卡片为圆角，角外为透明）
    assert img.getpixel((0, 0))[3] == 0


async def test_local_provider_render_foreground(tmp_path) -> None:
    out = tmp_path / "fg.png"
    provider = LocalDigitalHumanProvider()
    path = await provider.render_foreground(str(out), name="李老师")
    assert path == str(out)
    assert out.exists()
    assert provider.estimate_cost({}) == 0.0
    assert provider.provider_name == "local_digital_human"


def test_cloud_factory_none_this_round() -> None:
    # 本轮云端真机数字人未接入，工厂恒返回 None → 合成层用本地兜底
    assert get_digital_human_provider() is None
