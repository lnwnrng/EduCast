"""视频模板模型 — 模板市场与自定义模板。"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.user import User


class VideoTemplate(BaseMixin, Base):
    """视频模板 — 定义视频风格、配色、片头片尾等配置。

    支持:
    - 系统预设模板 (is_system=True)
    - 用户自定义模板
    - 模板分享 (is_public=True)
    """

    __tablename__ = "video_templates"

    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    category: Mapped[str] = mapped_column(
        String(30), default="general",
    )
    # JSON 配置: 配色、字体、片头片尾时长、转场效果等
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 预览图 URL
    preview_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 是否为系统内置模板
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    # 是否公开分享
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    # 使用次数统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    # 创建者
    creator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True,
    )
    # 排序权重
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # ── 关系 ─────────────────────────────────────────────
    creator: Mapped["User | None"] = relationship(
        foreign_keys=[creator_id],
    )
