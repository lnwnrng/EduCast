"""脚本管理 API — IR 操作。

提供 IR 的 CRUD 接口:
  - GET  /scripts/projects/{id}/script     — 获取当前 IR
  - PUT  /scripts/projects/{id}/script     — 更新 IR（教师编辑后保存）
  - POST /scripts/projects/{id}/script/generate — 触发 LLM 编排（模块二）
  - POST /scripts/projects/{id}/script/approve  — 审核通过
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import ResourceNotFoundException
from app.ir.schema import CourseIR
from app.ir.validator import validate_ir
from app.schemas.common import SuccessResponse
from app.services.parser_service import ParserService

router = APIRouter(prefix="/scripts", tags=["脚本管理"])

_parser_service = ParserService()


@router.get("/projects/{project_id}/script")
async def get_script(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取项目当前 IR 脚本。

    从文件系统加载最新版本的 IR JSON。
    """
    ir = await _parser_service.load_ir(str(project_id))
    if ir is None:
        raise ResourceNotFoundException(
            f"项目 {project_id} 尚未生成 IR 脚本"
        )
    return {
        "project_id": str(project_id),
        "ir": ir.model_dump(),
    }


@router.put("/projects/{project_id}/script")
async def update_script(
    project_id: UUID,
    ir_data: dict,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """更新 IR 脚本（教师编辑后保存）。

    校验 IR → 保存新版本 → 返回验证结果。
    """
    # 校验 IR 格式
    try:
        ir = CourseIR.model_validate(ir_data)
    except Exception as exc:
        raise ResourceNotFoundException(
            f"IR 数据格式错误: {exc}"
        ) from exc

    # 验证完整性
    errors = validate_ir(ir)

    # 查找当前最大版本号并递增
    current_ir = await _parser_service.load_ir(str(project_id))
    new_version = (current_ir.version + 1) if current_ir else 1
    ir.version = new_version

    # 保存
    ir_path = await _parser_service.save_ir(
        ir, str(project_id), version=new_version
    )

    return SuccessResponse(
        message="脚本已更新",
        data={
            "version": new_version,
            "ir_path": ir_path,
            "validation_warnings": errors,
        },
    )


@router.post("/projects/{project_id}/script/generate")
async def generate_script(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """触发 LLM 脚本编排。

    TODO(模块二): 创建编排任务，调用 ScriptWriter。
    """
    # 确认 IR 存在
    ir = await _parser_service.load_ir(str(project_id))
    if ir is None:
        raise ResourceNotFoundException(
            f"项目 {project_id} 尚未生成 IR，请先上传课件"
        )

    return SuccessResponse(
        message="脚本编排任务已创建（待模块二实现）",
        data={"project_id": str(project_id)},
    )


@router.post("/projects/{project_id}/script/approve")
async def approve_script(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """审核通过脚本 — 推进任务到生成阶段。

    TODO(模块三): 更新任务状态为 GENERATING。
    """
    return SuccessResponse(
        message="脚本审核通过，即将开始生成（待模块三实现）"
    )
