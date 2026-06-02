"""成本估算 / 配额护栏 / 汇总测试。"""

from app.providers.digital_human.placeholder import PlaceholderDigitalHumanProvider
from app.providers.video_gen.placeholder import PlaceholderVideoGenProvider


def test_digital_human_estimate_by_duration() -> None:
    provider = PlaceholderDigitalHumanProvider()
    # 默认费率 0.5 元/秒
    assert provider.estimate_cost({"duration_sec": 10}) == 5.0
    assert provider.estimate_cost({}) == 0.0


def test_video_gen_estimate_by_duration() -> None:
    provider = PlaceholderVideoGenProvider()
    # 默认费率 1.0 元/秒
    assert provider.estimate_cost({"duration_sec": 5}) == 5.0
    assert provider.estimate_cost({}) == 0.0
