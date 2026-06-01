"""文件上传 API。"""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.config import Settings
from app.pipeline.parser import SUPPORTED_EXTENSIONS
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/upload", tags=["文件上传"])


@router.post("/document", response_model=SuccessResponse)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SuccessResponse:
    """上传课件文档。

    支持: .pptx, .pdf, .docx, .md, .txt
    """
    # 校验文件类型
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"不支持的文件类型: {ext}。"
            f"支持: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # 保存文件
    upload_dir = os.path.join(settings.STORAGE_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename or "upload")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # TODO: 创建解析任务（Task），触发 BackgroundTask 解析
    return SuccessResponse(
        message="文件上传成功",
        data={
            "filename": file.filename,
            "file_path": file_path,
            "file_size": len(content),
            "file_type": ext,
        },
    )
