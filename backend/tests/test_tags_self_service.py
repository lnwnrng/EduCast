"""标签自助化测试 — 普通用户可直接创建/去重/更新/删除标签。"""


async def test_non_admin_can_create_tag(non_admin_auth_client):
    """普通用户可直接创建标签（无需管理员）。"""
    resp = await non_admin_auth_client.post(
        "/api/v1/tags/", json={"name": "高等数学", "color": "#1677ff"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "高等数学"
    assert body["color"] == "#1677ff"
    assert body["project_count"] == 0
    assert "id" in body


async def test_create_tag_dedup_by_name(non_admin_auth_client):
    """同名标签创建返回已存在的标签（按 name 去重）。"""
    r1 = await non_admin_auth_client.post(
        "/api/v1/tags/", json={"name": "线性代数", "color": "#aaaaaa"}
    )
    assert r1.status_code == 200
    first = r1.json()
    # 再次创建同名（即便颜色不同也不新建）
    r2 = await non_admin_auth_client.post(
        "/api/v1/tags/", json={"name": "线性代数", "color": "#bbbbbb"}
    )
    assert r2.status_code == 200
    second = r2.json()
    assert second["id"] == first["id"]
    # 返回的是已存在记录，颜色保持首次创建值
    assert second["color"] == "#aaaaaa"


async def test_non_admin_can_list_tags(non_admin_auth_client):
    """普通用户可读标签列表。"""
    await non_admin_auth_client.post("/api/v1/tags/", json={"name": "概率论"})
    resp = await non_admin_auth_client.get("/api/v1/tags/")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "概率论" in names


async def test_non_admin_can_update_tag(non_admin_auth_client):
    """普通用户可更新标签。"""
    created = (
        await non_admin_auth_client.post(
            "/api/v1/tags/", json={"name": "离散数学", "color": "#111111"}
        )
    ).json()
    resp = await non_admin_auth_client.put(
        f"/api/v1/tags/{created['id']}",
        json={"name": "离散数学（更新）", "color": "#222222"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "离散数学（更新）"
    assert body["color"] == "#222222"


async def test_non_admin_can_delete_tag(non_admin_auth_client):
    """普通用户可删除标签（硬删 + 清理 M2M，再次删除应 404）。"""
    created = (
        await non_admin_auth_client.post(
            "/api/v1/tags/", json={"name": "要删除的标签"}
        )
    ).json()
    tag_id = created["id"]
    resp = await non_admin_auth_client.delete(f"/api/v1/tags/{tag_id}")
    assert resp.status_code == 200
    # 再次删除应 404
    again = await non_admin_auth_client.delete(f"/api/v1/tags/{tag_id}")
    assert again.status_code == 404
