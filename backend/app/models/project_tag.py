"""项目-标签 多对多关联表。"""

from sqlalchemy import Column, ForeignKey, Table

from app.models.base import Base

project_tag = Table(
    "project_tags",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)
