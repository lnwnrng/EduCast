"""资源网盘化测试 — 文件夹层级 / 移动 / 环检测 / 级联删除 / 权限。"""

import uuid

from app.models.project import Project
from app.models.resource import Resource


async def _make_project(db_session, user_id):
    """在测试 DB 直接建一个项目（属 user_id）。"""
    project = Project(
        title="网盘测试项目",
        subject="",
        grade="",
        template="micro_lecture",
        status="draft",
        user_id=user_id,
    )
    db_session.add(project)
    await db_session.flush()
    return project


async def test_create_folder_and_list_children(auth_client, db_session, test_user):
    """建文件夹后能在 children 列表里看到。"""
    project = await _make_project(db_session, test_user.id)
    resp = await auth_client.post(
        "/api/v1/resources/folders",
        json={"project_id": str(project.id), "name": "子文件夹A"},
    )
    assert resp.status_code == 201
    folder = resp.json()
    assert folder["is_folder"] is True
    assert folder["name"] == "子文件夹A"
    assert folder["parent_id"] is None  # 项目根下

    # 列出项目根子项
    lst = await auth_client.get(f"/api/v1/resources/children?project_id={project.id}")
    assert lst.status_code == 200
    items = lst.json()
    assert any(i["id"] == folder["id"] and i["is_folder"] for i in items)


async def test_move_resource_into_folder_and_back(auth_client, db_session, test_user):
    """资源可移入文件夹，再移回根。"""
    project = await _make_project(db_session, test_user.id)
    res = Resource(
        project_id=project.id,
        resource_type="video",
        title="成片 第1版",
        name="成片 第1版",
        file_path="/tmp/fake.mp4",
        is_folder=False,
    )
    db_session.add(res)
    await db_session.flush()

    folder = (
        await auth_client.post(
            "/api/v1/resources/folders",
            json={"project_id": str(project.id), "name": "收纳"},
        )
    ).json()
    fid = folder["id"]

    # 移入文件夹
    mv = await auth_client.patch(
        f"/api/v1/resources/{res.id}", json={"parent_id": fid}
    )
    assert mv.status_code == 200
    assert mv.json()["parent_id"] == fid

    # 文件夹 children 应包含该资源
    children = (
        await auth_client.get(
            f"/api/v1/resources/children?project_id={project.id}&parent_id={fid}"
        )
    ).json()
    assert any(c["id"] == str(res.id) for c in children)

    # 移回根（parent_id 显式 null）
    back = await auth_client.patch(
        f"/api/v1/resources/{res.id}", json={"parent_id": None}
    )
    assert back.status_code == 200
    assert back.json()["parent_id"] is None


async def test_move_folder_into_own_descendant_rejected(
    auth_client, db_session, test_user
):
    """不能把文件夹移入自己的子孙（环检测 → 422）。"""
    project = await _make_project(db_session, test_user.id)
    root_folder = (
        await auth_client.post(
            "/api/v1/resources/folders",
            json={"project_id": str(project.id), "name": "外层"},
        )
    ).json()
    child_folder = (
        await auth_client.post(
            "/api/v1/resources/folders",
            json={
                "project_id": str(project.id),
                "name": "内层",
                "parent_id": root_folder["id"],
            },
        )
    ).json()
    # 把外层移入内层 → 应被拒（环）
    resp = await auth_client.patch(
        f"/api/v1/resources/{root_folder['id']}",
        json={"parent_id": child_folder["id"]},
    )
    assert resp.status_code == 422
    # 外层仍在根
    after = await auth_client.get(f"/api/v1/resources/children?project_id={project.id}")
    assert any(i["id"] == root_folder["id"] for i in after.json())


async def test_rename_resource(auth_client, db_session, test_user):
    """重命名资源/文件夹。"""
    project = await _make_project(db_session, test_user.id)
    folder = (
        await auth_client.post(
            "/api/v1/resources/folders",
            json={"project_id": str(project.id), "name": "原名"},
        )
    ).json()
    resp = await auth_client.patch(
        f"/api/v1/resources/{folder['id']}", json={"name": "新名"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名"


async def test_delete_folder_cascades(auth_client, db_session, test_user):
    """删除文件夹级联软删其下资源/子文件夹。"""
    project = await _make_project(db_session, test_user.id)
    parent = (
        await auth_client.post(
            "/api/v1/resources/folders",
            json={"project_id": str(project.id), "name": "父夹"},
        )
    ).json()
    child = (
        await auth_client.post(
            "/api/v1/resources/folders",
            json={
                "project_id": str(project.id),
                "name": "子夹",
                "parent_id": parent["id"],
            },
        )
    ).json()
    res = Resource(
        project_id=project.id,
        resource_type="subtitle",
        title="字幕",
        name="字幕",
        file_path="/tmp/fake.srt",
        parent_id=uuid.UUID(child["id"]),
    )
    db_session.add(res)
    await db_session.flush()

    # 删除父夹
    resp = await auth_client.delete(f"/api/v1/resources/{parent['id']}")
    assert resp.status_code == 200

    # 子夹与资源都应软删 → GET 单条应 404
    g1 = await auth_client.get(f"/api/v1/resources/{child['id']}")
    g2 = await auth_client.get(f"/api/v1/resources/{res.id}")
    assert g1.status_code == 404
    assert g2.status_code == 404


async def test_non_member_cannot_access_project_resources(
    non_admin_auth_client, db_session, test_user
):
    """非项目成员不能在他人项目建文件夹（403）。"""
    project = await _make_project(db_session, test_user.id)  # 属于 admin
    resp = await non_admin_auth_client.post(
        "/api/v1/resources/folders",
        json={"project_id": str(project.id), "name": "越权"},
    )
    assert resp.status_code == 403
