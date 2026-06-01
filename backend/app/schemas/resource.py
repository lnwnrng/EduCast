"""资源 Schema。"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ResourceResponse(BaseModel):
    """资源响应。"""

    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    resource_type: str
    title: str
    file_path: str
    file_size: int
    mime_type: Optional[str] = None
    version: int
    watermark_applied: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
