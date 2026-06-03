"""数字人 Provider 子包（模块四）。"""

from app.providers.digital_human.local import LocalDigitalHumanProvider


def get_digital_human_provider():
    """返回云端数字人 Provider。

    本轮云端真机 API 尚未接入，恒返回 ``None`` → 合成层使用
    ``LocalDigitalHumanProvider`` 渲染本地讲师画中画。

    接入真机后：依 ``DIGITAL_HUMAN_API_KEY`` 返回对应 vendor Provider（实现
    ``generate`` 取回口播视频作前景），合成层与成本护栏均无需改动——计费已随
    Key 自动生效（见 ``cost_service._is_billed``）。
    """
    return None


__all__ = ["LocalDigitalHumanProvider", "get_digital_human_provider"]
