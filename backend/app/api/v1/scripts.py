"""脚本管理 API — IR 操作。

提供 IR 的 CRUD 接口:
  - GET  /scripts/projects/{id}/script     — 获取当前 IR
  - PUT  /scripts/projects/{id}/script     — 更新 IR（教师编辑后保存）
  - POST /scripts/projects/{id}/script/generate — 触发 LLM 编排（模块二）
  - POST /scripts/projects/{id}/script/approve  — 审核通过
"""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.database import async_session_factory
from app.exceptions import ResourceNotFoundException
from app.ir.schema import CourseIR
from app.ir.validator import validate_ir
from app.models.task import Task
from app.schemas.common import SuccessResponse
from app.services.composition_service import CompositionService
from app.services.cost_service import check_quota, estimate_ir_cost
from app.services.parser_service import ParserService
from app.services.scriptwriter_service import ScriptwriterService

router = APIRouter(prefix="/scripts", tags=["脚本管理"])


class ApproveScriptRequest(BaseModel):
    """审核放行请求体。config 可含 tts_voice 等生成参数（可选）。"""

    config: dict[str, Any] | None = None


_parser_service = ParserService()


async def _run_orchestrate_in_background(
    project_id: str,
    task_id: str,
) -> None:
    """后台执行 LLM 脚本编排（独立 DB session）。"""
    async with async_session_factory() as db:
        try:
            await ScriptwriterService().orchestrate(
                project_id=project_id,
                task_id=task_id,
                db=db,
            )
        except Exception:
            # orchestrate 内部已处理错误状态更新
            pass


async def _run_composition_in_background(
    project_id: str,
    task_id: str,
) -> None:
    """后台执行模块三视频合成（独立 DB session）。"""
    async with async_session_factory() as db:
        try:
            await CompositionService().compose(
                project_id=project_id,
                task_id=task_id,
                db=db,
            )
        except Exception:
            # compose 内部已处理错误状态更新
            pass


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
        raise ResourceNotFoundException(f"项目 {project_id} 尚未生成 IR 脚本")
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
        raise ResourceNotFoundException(f"IR 数据格式错误: {exc}") from exc

    # 验证完整性
    errors = validate_ir(ir)

    # 查找当前最大版本号并递增
    current_ir = await _parser_service.load_ir(str(project_id))
    new_version = (current_ir.version + 1) if current_ir else 1
    ir.version = new_version

    # 保存
    ir_path = await _parser_service.save_ir(ir, str(project_id), version=new_version)

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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """触发 LLM 脚本编排（手动「重新编排」）。

    创建一个 scripting 任务并在后台调用 ScriptWriter（GLM-4.7-Flash），
    返回 task_id 供前端轮询进度。
    """
    # 确认 IR 存在
    ir = await _parser_service.load_ir(str(project_id))
    if ir is None:
        raise ResourceNotFoundException(f"项目 {project_id} 尚未生成 IR，请先上传课件")

    # 创建编排任务
    task = Task(
        project_id=project_id,
        task_type="scripting",
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    await db.commit()

    # 后台执行编排（独立 session）
    background_tasks.add_task(
        _run_orchestrate_in_background,
        project_id=str(project_id),
        task_id=str(task.id),
    )

    return SuccessResponse(
        message="脚本编排任务已创建",
        data={"project_id": str(project_id), "task_id": str(task.id)},
    )


@router.post("/projects/{project_id}/script/approve")
async def approve_script(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    data: ApproveScriptRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """审核通过脚本 — 人在环放行，触发模块三视频生成与合成。

    创建生成任务并在后台执行 CompositionService（配音 + 课件渲染 + FFmpeg 合成
    + 入库），返回 task_id 供前端轮询进度。可选 body `{config:{tts_voice}}` 透传
    生成参数（音色等）。重复调用即「重新生成」，产出新的成片版本。
    """
    ir = await _parser_service.load_ir(str(project_id))
    if ir is None:
        raise ResourceNotFoundException(f"项目 {project_id} 尚未生成 IR，无法生成视频")

    # 成本护栏：按"实际会计费"的成本校验配额（超额抛 CostLimitException → 429）
    estimate = estimate_ir_cost(ir)
    await check_quota(db, str(project_id), estimate.chargeable)

    config = data.config if data else None
    task = Task(
        project_id=project_id,
        task_type="full_pipeline",
        status="generating",
        progress=50,
        estimated_cost=estimate.chargeable,
        config_json=(json.dumps(config, ensure_ascii=False) if config else None),
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    await db.commit()

    background_tasks.add_task(
        _run_composition_in_background,
        project_id=str(project_id),
        task_id=str(task.id),
    )

    return SuccessResponse(
        message="脚本审核通过，已开始生成视频",
        data={
            "project_id": str(project_id),
            "task_id": str(task.id),
            "estimated_cost": estimate.chargeable,
            "potential_cost": estimate.total,
        },
    )
