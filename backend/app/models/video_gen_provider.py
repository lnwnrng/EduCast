"""视频生成 Provider 配置模型 — 多模型管理（cc-switch 风格）。

存储管理员在前端配置的视频生成 provider 实例（CogVideoX / Kling / MiniMax）
及其 API Key、base_url、模型型号。同一时刻仅一条 `is_active=True` 的配置
生效，由 `providers/video_gen` 工厂读取并镜像到运行时设置供同步路径使用。
"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class VideoGenProviderConfig(BaseMixin, Base):
    """视频生成 Provider 配置实例 — 一条记录对应一个可调用的视频生成账号。

    provider_type: cogvideox | kling | minimax
    """

    __tablename__ = "video_gen_provider_configs"

    provider_type: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(100))
    api_key: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str] = mapped_column(String(255))
    model_id: Mapped[str] = mapped_column(String(100))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
