"""项目 API 基础测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    """测试根端点。"""
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "课影 EduCast API"


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient) -> None:
    """测试创建项目。"""
    resp = await client.post(
        "/api/v1/projects/",
        json={
            "title": "高等数学 - 导数",
            "subject": "mathematics",
            "grade": "college_freshman",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "高等数学 - 导数"
    assert data["status"] == "draft"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient) -> None:
    """测试项目列表。"""
    # 创建一个项目
    await client.post(
        "/api/v1/projects/",
        json={"title": "测试项目"},
    )

    resp = await client.get("/api/v1/projects/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient) -> None:
    """测试获取项目详情。"""
    # 创建
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"title": "详情测试"},
    )
    project_id = create_resp.json()["id"]

    # 获取
    resp = await client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "详情测试"


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient) -> None:
    """测试更新项目。"""
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"title": "更新前"},
    )
    project_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"title": "更新后"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "更新后"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient) -> None:
    """测试删除项目。"""
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"title": "待删除"},
    )
    project_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "项目已删除"
