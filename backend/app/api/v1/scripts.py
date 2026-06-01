"""脚本管理 API — IR 操作。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/scripts", tags=["脚本管理"])


@router.get("/projects/{project_id}/script")
async def get_script(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取项目当前 IR 脚本。

    TODO: 从数据库/文件系统加载 IR JSON。
    """
    # TODO: 实现 IR 加载
    return {"project_id": str(project_id), "ir": None}


@router.put("/projects/{project_id}/script")
async def update_script(
    project_id: UUID,
    ir_data: dict,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """更新 IR 脚本（教师编辑后保存）。

    TODO: 校验 IR → 保存 → 创建版本快照。
    """
    # TODO: 实现 IR 更新与版本管理
    return SuccessResponse(message="脚本已更新")


@router.post("/projects/{project_id}/script/generate")
async def generate_script(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """触发 LLM 脚本编排。

    TODO: 创建编排任务，调用 ScriptWriter。
    """
    return SuccessResponse(
        message="脚本编排任务已创建",
        data={"project_id": str(project_id)},
    )


@router.post("/projects/{project_id}/script/approve")
async def approve_script(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """审核通过脚本 — 推进任务到生成阶段。

    TODO: 更新任务状态为 GENERATING。
    """
    return SuccessResponse(message="脚本审核通过，即将开始生成")
