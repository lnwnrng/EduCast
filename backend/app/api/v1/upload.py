"""文件上传 API — 上传课件并触发解析流水线。

流程:
  POST /upload/document → 保存文件 → 创建 Project + Task → 后台解析 → 返回 IDs
  POST /upload/batch    → 多文件/ZIP 上传 → 批量创建项目
"""

import logging
import os
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.config import Settings, settings
from app.database import async_session_factory
from app.exceptions import CostLimitException, ValidationException
from app.middleware.auth import get_current_user_from_cookie
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.pipeline.parser import SUPPORTED_EXTENSIONS
from app.schemas.common import SuccessResponse
from app.services.composition_service import CompositionService
from app.services.cost_service import check_quota, estimate_ir_cost
from app.services.parser_service import ParserService
from app.services.scriptwriter_service import ScriptwriterService

router = APIRouter(prefix="/upload", tags=["文件上传"])

logger = logging.getLogger(__name__)

# 文件类型魔数(magic bytes)校验表
_MAGIC_BYTES: dict[str, list[bytes]] = {
    ".pptx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],  # ZIP-based (OOXML)
    ".docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],  # ZIP-based (OOXML)
    ".pdf": [b"%PDF"],
    ".md": [],  # 文本文件无固定魔数，跳过校验
    ".txt": [],  # 文本文件无固定魔数，跳过校验
}


async def _run_parse_in_background(
    file_path: str,
    file_type: str,
    project_id: str,
    task_id: str,
) -> None:
    """后台执行 文档解析 → LLM 脚本编排。

    解析成功后状态推进到 scripting，紧接着自动跑 LLM 编排，最终落到
    reviewing 待教师审核（模块二「上传后自动编排」）。

    注意: 后台任务必须创建自己的 DB session，
    不能复用请求 handler 的 session（响应后已关闭）。
    """
    async with async_session_factory() as db:
        try:
            await ParserService().parse_document(
                file_path=file_path,
                file_type=file_type,
                project_id=project_id,
                task_id=task_id,
                db=db,
                advance_status="scripting",
                advance_progress=45,
            )
        except Exception:
            # parse_document 内部已处理错误状态更新，解析失败则不再编排
            logger.error(
                "后台解析异常: project=%s, task=%s",
                project_id,
                task_id,
                exc_info=True,
            )
            return

        try:
            await ScriptwriterService().orchestrate(
                project_id=project_id,
                task_id=task_id,
                db=db,
            )
        except Exception:
            # orchestrate 内部已处理错误状态更新
            logger.error(
                "后台编排异常: project=%s, task=%s",
                project_id,
                task_id,
                exc_info=True,
            )

        # 一键全自动：跨过人工审核直接生成（仍走成本护栏）
        if settings.SKIP_REVIEW:
            await _auto_generate(project_id, task_id, db)


async def _auto_generate(project_id: str, task_id: str, db: AsyncSession) -> None:
    """SKIP_REVIEW 模式：预估成本 + 配额护栏 + 直接合成成片。"""
    ir = await ParserService().load_ir(project_id)
    if ir is None:
        return
    try:
        estimate = estimate_ir_cost(ir)
        await check_quota(db, project_id, estimate.chargeable)
    except CostLimitException as exc:
        task = await db.get(Task, uuid.UUID(task_id))
        if task:
            task.status = "failed"
            task.error_message = f"成本超限，已拦截自动生成: {exc.message}"
            await db.commit()
        return
    except Exception:
        return

    task = await db.get(Task, uuid.UUID(task_id))
    if task:
        task.estimated_cost = estimate.chargeable
        await db.commit()

    try:
        await CompositionService().compose(
            project_id=project_id, task_id=task_id, db=db
        )
    except Exception:
        # compose 内部已处理错误状态更新
        logger.error(
            "后台合成异常: project=%s, task=%s",
            project_id,
            task_id,
            exc_info=True,
        )


@router.post("/document", response_model=SuccessResponse)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    template: str = Form("micro_lecture"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user_from_cookie),
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

    # 使用 UUID 前缀 + 安全文件名防止路径遍历
    safe_name = Path(filename).name
    safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = os.path.join(upload_dir, safe_filename)

    content = await file.read()
    if not content:
        raise ValidationException("上传文件为空")

    # 文件内容嗅探(magic bytes)校验，防止扩展名伪造
    expected_magics = _MAGIC_BYTES.get(ext)
    if expected_magics:  # 空列表表示文本文件，跳过校验
        if not any(content.startswith(magic) for magic in expected_magics):
            raise ValidationException(
                f"文件内容与扩展名 {ext} 不匹配，"
                "请确认上传的是真实文件而非重命名文件"
            )

    with open(file_path, "wb") as f:
        f.write(content)

    # 3. 创建 Project
    project_title = Path(filename).stem
    project = Project(
        title=project_title,
        status="parsing",
        user_id=current_user.id,
        template=template,
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

    # 提交当前事务，确保 Project/Task 在后台任务可见
    await db.commit()

    # 5. 触发后台解析（使用独立 DB session）
    background_tasks.add_task(
        _run_parse_in_background,
        file_path=file_path,
        file_type=ext,
        project_id=str(project.id),
        task_id=str(task.id),
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


# ── 批量上传 + ZIP 解压 ────────────────────────────────────


def _extract_zip_to_temp(content: bytes, upload_dir: str) -> list[str]:
    """解压 ZIP 文件到 upload_dir，返回解压出的支持文件路径列表。

    只提取 SUPPORTED_EXTENSIONS 中的文件，忽略 macOS __MACOSX 等垃圾目录。
    """
    extracted: list[str] = []
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            # 安全检查：防止 ZIP slip 攻击
            for member in zf.namelist():
                if member.startswith("/") or ".." in member:
                    logger.warning("跳过不安全的 ZIP 条目: %s", member)
                    continue
                # 跳过 macOS 元数据目录
                if "__MACOSX" in member or member.startswith("."):
                    continue
                ext = Path(member).suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(member).name}"
                    out_path = os.path.join(upload_dir, safe_name)
                    with zf.open(member) as src, open(out_path, "wb") as dst:
                        dst.write(src.read())
                    extracted.append(out_path)
    finally:
        os.unlink(tmp_path)

    return extracted


@router.post("/batch", response_model=SuccessResponse)
async def upload_batch(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    template: str = Form("micro_lecture"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """批量上传课件，支持多文件或单个 ZIP 压缩包。

    - 多个文件: 每个文件创建一个独立项目
    - 单个 ZIP: 自动解压，每个支持的文件创建一个独立项目

    Returns:
        包含每个项目的 project_id 和 task_id 列表
    """
    upload_dir = os.path.join(settings.STORAGE_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # 收集所有要处理的文件：(file_path, file_ext, original_name)
    file_entries: list[tuple[str, str, str]] = []

    for upload_file in files:
        filename = upload_file.filename or "upload"
        ext = Path(filename).suffix.lower()
        content = await upload_file.read()

        if not content:
            continue

        # ZIP 文件：解压并收集内部文件
        if ext == ".zip":
            extracted = _extract_zip_to_temp(content, upload_dir)
            for fpath in extracted:
                fext = Path(fpath).suffix.lower()
                fname = Path(fpath).name
                file_entries.append((fpath, fext, fname))
            logger.info(
                "ZIP 解压完成: %s → %d 个文件",
                filename,
                len(extracted),
            )
        elif ext in SUPPORTED_EXTENSIONS:
            # 普通文件：直接保存
            safe_name = Path(filename).name
            safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
            file_path = os.path.join(upload_dir, safe_filename)
            with open(file_path, "wb") as f:
                f.write(content)
            file_entries.append((file_path, ext, filename))
        else:
            logger.warning("批量上传跳过不支持的文件: %s", filename)

    if not file_entries:
        raise ValidationException(
            "未找到可处理的文件，请上传支持的格式或包含有效文件的 ZIP"
        )

    # 为每个文件创建 Project + Task
    results: list[dict] = []
    for file_path, file_ext, original_name in file_entries:
        project_title = Path(original_name).stem
        project = Project(
            title=project_title,
            status="parsing",
            user_id=current_user.id,
            template=template,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)

        task = Task(
            project_id=project.id,
            task_type="full_pipeline",
            status="pending",
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        await db.commit()

        background_tasks.add_task(
            _run_parse_in_background,
            file_path=file_path,
            file_type=file_ext,
            project_id=str(project.id),
            task_id=str(task.id),
        )

        results.append(
            {
                "project_id": str(project.id),
                "task_id": str(task.id),
                "filename": original_name,
                "file_type": file_ext,
            }
        )

    return SuccessResponse(
        message=f"批量上传成功，共创建 {len(results)} 个项目",
        data={"items": results, "total": len(results)},
    )
