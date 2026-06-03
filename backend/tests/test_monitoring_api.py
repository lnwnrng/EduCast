"""监控与成本 API 测试（直接播种 DB + IR，不走上传/网络，保持快与可重复）。"""

import pytest
from httpx import AsyncClient

from app.config import settings
from app.ir.schema import (
    ChapterIR,
    CourseIR,
    KnowledgePointIR,
    SceneIR,
    SceneType,
)
from app.models.project import Project
from app.models.task import Task
from app.services.parser_service import ParserService
from app.services.resource_service import ResourceService


async def _seed_project_with_ir(db_session, tmp_path) -> str:
    project = Project(title="监控测试课程", status="reviewing")
    db_session.add(project)
    await db_session.flush()
    db_session.add(
        Task(
            project_id=project.id,
            status="completed",
            estimated_cost=5.0,
            actual_cost=0.0,
        )
    )
    await db_session.commit()
    pid = str(project.id)

    # 含数字人分镜 → 成本预估非零
    scene = SceneIR(
        order=1,
        scene_type=SceneType.DIGITAL_HUMAN,
        narration_text="字" * 40,  # 40/4=10s × 0.5 = 5.0
    )
    kp = KnowledgePointIR(title="kp", scenes=[scene])
    ch = ChapterIR(title="ch", order=1, knowledge_points=[kp])
    ir = CourseIR(course_id=pid, title="监控测试课程", version=1, chapters=[ch])
    await ParserService().save_ir(ir, pid, version=1)
    return pid


@pytest.mark.asyncio
async def test_cost_estimate_summary_dashboard(
    client: AsyncClient, db_session, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    pid = await _seed_project_with_ir(db_session, tmp_path)

    # 成本预估（数字人 → 5.0）
    r1 = await client.get(f"/api/v1/projects/{pid}/cost-estimate")
    assert r1.status_code == 200
    body = r1.json()
    assert body["total"] == 5.0
    assert body["breakdown"].get("digital_human") == 5.0
    assert body["currency"] == "CNY"

    # 项目成本汇总
    r2 = await client.get(f"/api/v1/projects/{pid}/cost")
    assert r2.status_code == 200
    summary = r2.json()
    assert summary["task_count"] == 1
    assert summary["status_counts"] == {"completed": 1}
    assert summary["estimated_total"] == 5.0

    # 全局监控面板
    r3 = await client.get("/api/v1/monitoring/dashboard")
    assert r3.status_code == 200
    dash = r3.json()
    assert dash["task_count"] >= 1
    assert isinstance(dash["recent_tasks"], list)


@pytest.mark.asyncio
async def test_cost_estimate_without_ir_404(client: AsyncClient) -> None:
    create = await client.post("/api/v1/projects/", json={"title": "空项目"})
    project_id = create.json()["id"]
    resp = await client.get(f"/api/v1/projects/{project_id}/cost-estimate")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_workspace_aggregate_and_stale(
    client: AsyncClient, db_session, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    project = Project(title="工作台课程", status="completed")
    db_session.add(project)
    await db_session.flush()
    pid = str(project.id)

    scene = SceneIR(order=1, scene_type=SceneType.SLIDE, narration_text="讲解")
    ir = CourseIR(
        course_id=pid,
        title="工作台课程",
        version=1,
        chapters=[
            ChapterIR(
                title="章",
                order=1,
                knowledge_points=[KnowledgePointIR(title="kp", scenes=[scene])],
            )
        ],
    )
    await ParserService().save_ir(ir, pid, version=1)
    await ResourceService.create_resource(
        db_session,
        project.id,
        "video",
        "成片 第1版",
        "gen1.mp4",
        mime_type="video/mp4",
        version=1,
        metadata={"ir_version": 1},
    )
    await db_session.commit()

    r = await client.get(f"/api/v1/projects/{pid}/workspace")
    assert r.status_code == 200
    body = r.json()
    assert body["has_ir"] is True
    assert body["latest_ir_version"] == 1
    assert len(body["videos"]) == 1
    assert body["videos"][0]["version"] == 1
    assert body["videos"][0]["ir_version"] == 1
    assert body["is_stale"] is False
    assert body["cost_estimate"] is not None

    # 改脚本 → IR v2，成片仍基于 v1 → 过期
    ir.version = 2
    await ParserService().save_ir(ir, pid, version=2)
    r2 = await client.get(f"/api/v1/projects/{pid}/workspace")
    body2 = r2.json()
    assert body2["latest_ir_version"] == 2
    assert body2["is_stale"] is True
