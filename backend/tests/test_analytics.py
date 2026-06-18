"""学情分析 API 测试。"""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import Annotation
from app.models.project import Project
from app.models.resource import Resource
from app.models.task import Task


async def _seed_analytics_project(
    db_session: AsyncSession,
    user_id,
    *,
    add_deleted_task: bool = False,
    add_resources: bool = False,
    add_annotations: bool = False,
) -> str:
    """播种一个包含任务/资源/标注的项目，返回 project_id 字符串。"""
    project = Project(
        title="分析测试项目",
        status="completed",
        user_id=user_id,
    )
    db_session.add(project)
    await db_session.flush()

    # 正常任务
    db_session.add(
        Task(
            project_id=project.id,
            status="completed",
            task_type="full_pipeline",
            estimated_cost=5.0,
            actual_cost=3.0,
            progress=100,
        )
    )
    db_session.add(
        Task(
            project_id=project.id,
            status="scripting",
            task_type="full_pipeline",
            estimated_cost=2.0,
            actual_cost=0.0,
            progress=50,
        )
    )

    # 软删除任务（不应被统计）
    if add_deleted_task:
        db_session.add(
            Task(
                project_id=project.id,
                status="failed",
                task_type="full_pipeline",
                estimated_cost=10.0,
                actual_cost=8.0,
                deleted_at=datetime.now(UTC),
            )
        )

    # 资源
    if add_resources:
        db_session.add(
            Resource(
                project_id=project.id,
                resource_type="video",
                title="test_video",
                file_path="/storage/test.mp4",
                file_size=1024 * 1024,
            )
        )
        db_session.add(
            Resource(
                project_id=project.id,
                resource_type="image",
                title="test_image",
                file_path="/storage/test.png",
                file_size=512,
            )
        )

    # 标注
    if add_annotations:
        db_session.add(
            Annotation(
                project_id=project.id,
                user_id=user_id,
                timestamp=10.0,
                text="重要知识点",
            )
        )

    await db_session.flush()
    await db_session.commit()
    return str(project.id)


@pytest.mark.asyncio
async def test_project_analytics_basic(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
) -> None:
    """项目学情分析 — 基本正常响应。"""
    pid = await _seed_analytics_project(
        db_session, test_user.id,
        add_resources=True, add_annotations=True,
    )

    resp = await auth_client.get(f"/api/v1/projects/{pid}/analytics")
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert data["project_id"] == pid
    assert data["task_count"] == 2
    assert data["total_actual_cost"] == 3.0
    assert data["total_estimated_cost"] == 7.0
    assert data["status_counts"] == {"completed": 1, "scripting": 1}
    assert data["resource_count"] == 2
    assert data["video_count"] == 1
    assert data["annotation_count"] == 1
    assert len(data["recent_tasks"]) == 2


@pytest.mark.asyncio
async def test_project_analytics_soft_deleted_tasks_excluded(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
) -> None:
    """软删除任务不计入统计。"""
    pid = await _seed_analytics_project(
        db_session, test_user.id,
        add_deleted_task=True,
    )

    resp = await auth_client.get(f"/api/v1/projects/{pid}/analytics")
    assert resp.status_code == 200

    data = resp.json()["data"]
    # 软删除任务不应被计入（只有 2 个正常任务）
    assert data["task_count"] == 2
    # 软删除任务的 actual_cost=8.0 不应被计算
    assert data["total_actual_cost"] == 3.0
    assert "failed" not in data["status_counts"]


@pytest.mark.asyncio
async def test_project_analytics_invalid_uuid(
    auth_client: AsyncClient,
) -> None:
    """非法 UUID 应返回 422。"""
    resp = await auth_client.get("/api/v1/projects/not-a-uuid/analytics")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_project_analytics_not_found(
    auth_client: AsyncClient,
) -> None:
    """不存在的项目应返回 404。"""
    resp = await auth_client.get(f"/api/v1/projects/{uuid.uuid4()}/analytics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_project_analytics_unauthenticated(
    client: AsyncClient,
) -> None:
    """未登录用户应被拒绝。"""
    resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}/analytics")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_global_analytics(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
) -> None:
    """全局学情分析端点 — 跨项目汇总。"""
    await _seed_analytics_project(db_session, test_user.id)

    resp = await auth_client.get("/api/v1/projects/analytics")
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert data["project_count"] >= 1
    assert data["task_count"] >= 2
    assert "status_counts" in data
    assert "recent_tasks" in data
    # 全局端点不包含项目特有字段
    assert "storage_bytes" not in data
    assert "annotation_count" not in data


@pytest.mark.asyncio
async def test_project_analytics_access_control(
    non_admin_auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
) -> None:
    """普通用户无法查看他人项目的分析数据。"""
    # 用 admin 用户创建项目
    pid = await _seed_analytics_project(db_session, test_user.id)

    # 用普通用户访问 → 应返回 404（项目不存在或无权访问）
    resp = await non_admin_auth_client.get(f"/api/v1/projects/{pid}/analytics")
    assert resp.status_code == 404
