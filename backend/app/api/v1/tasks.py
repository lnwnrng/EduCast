"""任务管理 API。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie
from app.models.user import User
from app.schemas.task import SubTaskResponse, TaskCreate, TaskResponse
from app.services.task_service import TaskService

router = APIRouter(tags=["任务管理"])


@router.post(
    "/projects/{project_id}/tasks/",
    response_model=TaskResponse,
    status_code=201,
)
async def create_task(
    project_id: UUID,
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> TaskResponse:
    """为项目创建生成任务。"""
    task = await TaskService.create_task(db, project_id, data)
    return TaskResponse.model_validate(task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> TaskResponse:
    """获取任务详情与进度。"""
    task = await TaskService.get_task(db, task_id)
    return TaskResponse.model_validate(task)


@router.get(
    "/tasks/{task_id}/subtasks",
    response_model=list[SubTaskResponse],
)
async def get_subtasks(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[SubTaskResponse]:
    """获取子任务列表。"""
    subtasks = await TaskService.get_subtasks(db, task_id)
    return [SubTaskResponse.model_validate(s) for s in subtasks]


@router.post("/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> TaskResponse:
    """重试失败的任务。"""
    task = await TaskService.retry_task(db, task_id)
    return TaskResponse.model_validate(task)
