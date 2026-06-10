"""EduCast 数据库模型。"""

from app.models.audit_log import AuditLog
from app.models.base import Base, BaseMixin
from app.models.category import CourseCategory
from app.models.category_tag_request import CategoryTagRequest
from app.models.project import Project
from app.models import project_tag  # noqa: F401
from app.models.refresh_token import RefreshToken
from app.models.resource import Resource
from app.models.tag import Tag
from app.models.task import SubTask, Task
from app.models.user import User
from app.models.verification_code import VerificationCode

__all__ = [
    "AuditLog",
    "Base",
    "BaseMixin",
    "CategoryTagRequest",
    "CourseCategory",
    "Project",
    "RefreshToken",
    "Resource",
    "SubTask",
    "Tag",
    "Task",
    "User",
    "VerificationCode",
]