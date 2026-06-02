"""approve_script 成本护栏测试。"""

import pytest
from httpx import AsyncClient

from app.api.v1 import scripts as scripts_module
from app.config import settings
from app.ir.schema import (
    ChapterIR,
    CourseIR,
    KnowledgePointIR,
    SceneIR,
    SceneType,
)
from app.models.project import Project
from app.services.parser_service import ParserService


async def _seed_project(db_session) -> str:
    project = Project(title="审核测试", status="reviewing")
    db_session.add(project)
    await db_session.flush()
    await db_session.commit()
    return str(project.id)


def _ir(pid: str, scene_type: SceneType, narration: str = "") -> CourseIR:
    scene = SceneIR(order=1, scene_type=scene_type, narration_text=narration)
    kp = KnowledgePointIR(title="kp", scenes=[scene])
    ch = ChapterIR(title="ch", order=1, knowledge_points=[kp])
    return CourseIR(course_id=pid, title="c", version=1, chapters=[ch])


@pytest.mark.asyncio
async def test_approve_over_quota_returns_429(
    client: AsyncClient, db_session, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_COST_PER_PROJECT", 1.0)
    pid = await _seed_project(db_session)
    # 数字人旁白 40 字 → 估算 5.0 > 项目上限 1.0
    await ParserService().save_ir(
        _ir(pid, SceneType.DIGITAL_HUMAN, "字" * 40), pid, version=1
    )

    resp = await client.post(f"/api/v1/scripts/projects/{pid}/script/approve")
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_approve_free_stack_returns_200(
    client: AsyncClient, db_session, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))

    # 拦住后台合成，避免真实 ffmpeg/网络
    async def _noop(project_id: str, task_id: str) -> None:
        return None

    monkeypatch.setattr(scripts_module, "_run_composition_in_background", _noop)

    pid = await _seed_project(db_session)
    await ParserService().save_ir(_ir(pid, SceneType.SLIDE, "课件文本"), pid, version=1)

    resp = await client.post(f"/api/v1/scripts/projects/{pid}/script/approve")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "task_id" in data
    assert data["estimated_cost"] == 0.0
