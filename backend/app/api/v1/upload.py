"""文件上传 API — 上传课件并触发解析流水线。

流程:
  POST /upload/document → 保存文件 → 创建 Project + Task → 后台解析 → 返回 IDs
"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.config import Settings
from app.exceptions import ParseException, ValidationException
from app.models.project import Project
from app.models.task import Task
from app.pipeline.parser import SUPPORTED_EXTENSIONS
from app.schemas.common import SuccessResponse
from app.services.parser_service import ParserService

router = APIRouter(prefix="/upload", tags=["文件上传"])


async def _run_parse_in_background(
    file_path: str,
    file_type: str,
    project_id: str,
    task_id: str,
    db: AsyncSession,
) -> None:
    """后台执行文档解析。"""
    service = ParserService()
    await service.parse_document(
        file_path=file_path,
        file_type=file_type,
        project_id=project_id,
        task_id=task_id,
        db=db,
    )


@router.post("/document", response_model=SuccessResponse)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SuccessResponse:
    """上传课件文档并触发解析。

    支持: .pptx, .pdf, .docx, .md, .txt

    流程:
      1. 校验文件类型
      2. 保存文件到 storage/uploads/
      3. 创建 Project (status=draft)
      4. 创建 Task (status=pending, type=full_pipeline)
      5. 触发后台解析任务
      6. 返回 project_id 和 task_id
    """
    # 1. 校验文件类型
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValidationException(
            f"不支持的文件类型: {ext}。"
            f"支持: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # 2. 保存文件
    upload_dir = os.path.join(settings.STORAGE_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # 使用 UUID 前缀防止文件名冲突
    safe_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    file_path = os.path.join(upload_dir, safe_filename)

    content = await file.read()
    if not content:
        raise ValidationException("上传文件为空")

    with open(file_path, "wb") as f:
        f.write(content)

    # 3. 创建 Project
    project_title = Path(filename).stem
    project = Project(
        title=project_title,
        status="parsing",
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    # 4. 创建 Task
    task = Task(
        project_id=project.id,
        task_type="full_pipeline",
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # 5. 触发后台解析
    background_tasks.add_task(
        _run_parse_in_background,
        file_path=file_path,
        file_type=ext,
        project_id=str(project.id),
        task_id=str(task.id),
        db=db,
    )

    # 6. 返回结果
    return SuccessResponse(
        message="文件上传成功，解析任务已创建",
        data={
            "project_id": str(project.id),
            "task_id": str(task.id),
            "filename": filename,
            "file_path": file_path,
            "file_size": len(content),
            "file_type": ext,
        },
    )
