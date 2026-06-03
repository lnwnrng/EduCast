"""成本估算 / 配额护栏 / 汇总测试。"""

import pytest

from app.config import settings
from app.exceptions import CostLimitException
from app.ir.schema import (
    ChapterIR,
    CourseIR,
    KnowledgePointIR,
    SceneIR,
    SceneType,
    VisualSpec,
)
from app.models.project import Project
from app.models.resource import Resource
from app.models.task import Task
from app.providers.digital_human.placeholder import PlaceholderDigitalHumanProvider
from app.providers.video_gen.placeholder import PlaceholderVideoGenProvider
from app.services.cost_service import (
    check_quota,
    estimate_ir_cost,
    project_cost_summary,
)


def test_digital_human_estimate_by_duration() -> None:
    provider = PlaceholderDigitalHumanProvider()
    # 默认费率 0.5 元/秒
    assert provider.estimate_cost({"duration_sec": 10}) == 5.0
    assert provider.estimate_cost({}) == 0.0


def test_video_gen_estimate_by_duration() -> None:
    provider = PlaceholderVideoGenProvider()
    # 默认费率 1.0 元/秒
    assert provider.estimate_cost({"duration_sec": 5}) == 5.0
    assert provider.estimate_cost({}) == 0.0


def _ir_with(*scene_types: SceneType, narration: str = "") -> CourseIR:
    scenes = [
        SceneIR(
            order=i + 1,
            scene_type=t,
            narration_text=narration,
            visual_spec=VisualSpec(),
        )
        for i, t in enumerate(scene_types)
    ]
    kp = KnowledgePointIR(title="kp", scenes=scenes)
    ch = ChapterIR(title="ch", order=1, knowledge_points=[kp])
    return CourseIR(title="c", chapters=[ch])


def test_estimate_potential_but_not_chargeable_without_keys(monkeypatch) -> None:
    # 未配置付费 API Key → 潜在成本算满，实际计费为 0（降级免费课件页）
    monkeypatch.setattr(settings, "DIGITAL_HUMAN_API_KEY", "")
    monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
    # CogVideoX 同平台会回退 ZHIPU_API_KEY，故一并清空以验证"全无付费能力"
    monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
    ir = _ir_with(
        SceneType.SLIDE,
        SceneType.DIGITAL_HUMAN,
        SceneType.GENERATIVE_CLIP,
        narration="字" * 40,  # 40/4=10s × 0.5 = 5.0；生成式 5s × 1.0 = 5.0
    )
    est = estimate_ir_cost(ir)
    assert est.breakdown.get("digital_human") == 5.0
    assert est.breakdown.get("generative_clip") == 5.0
    assert "slide" not in est.breakdown
    assert est.total == 10.0
    assert est.chargeable == 0.0


def test_estimate_chargeable_when_providers_active(monkeypatch) -> None:
    # 配好 Key（付费能力激活）→ 实际计费 = 潜在成本
    monkeypatch.setattr(settings, "DIGITAL_HUMAN_API_KEY", "k")
    monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "k")
    ir = _ir_with(
        SceneType.SLIDE,
        SceneType.DIGITAL_HUMAN,
        SceneType.GENERATIVE_CLIP,
        narration="字" * 40,
    )
    est = estimate_ir_cost(ir)
    assert est.total == 10.0
    assert est.chargeable == 10.0


def test_estimate_free_stack_is_zero() -> None:
    ir = _ir_with(SceneType.SLIDE, SceneType.FORMULA_ANIMATION, narration="任意")
    est = estimate_ir_cost(ir)
    assert est.total == 0.0
    assert est.chargeable == 0.0
    assert est.breakdown == {}


async def test_check_quota_pass(db_session) -> None:
    project = Project(title="p")
    db_session.add(project)
    await db_session.flush()
    await check_quota(db_session, str(project.id), 5.0)  # 不抛


async def test_check_quota_over_task(db_session) -> None:
    project = Project(title="p")
    db_session.add(project)
    await db_session.flush()
    # 超单任务上限（默认 10）
    with pytest.raises(CostLimitException):
        await check_quota(db_session, str(project.id), settings.MAX_COST_PER_TASK + 1)


async def test_check_quota_over_project(db_session) -> None:
    project = Project(title="p")
    db_session.add(project)
    await db_session.flush()
    # 已花费接近项目上限（默认 100）
    db_session.add(Task(project_id=project.id, status="completed", actual_cost=98.0))
    await db_session.flush()
    with pytest.raises(CostLimitException):
        await check_quota(db_session, str(project.id), 5.0)


async def test_project_cost_summary(db_session) -> None:
    project = Project(title="p")
    db_session.add(project)
    await db_session.flush()
    db_session.add_all(
        [
            Task(
                project_id=project.id,
                status="completed",
                estimated_cost=4.0,
                actual_cost=3.0,
            ),
            Task(project_id=project.id, status="failed"),
            Resource(
                project_id=project.id,
                resource_type="video",
                title="v",
                file_path="x.mp4",
                file_size=1000,
            ),
        ]
    )
    await db_session.flush()

    summary = await project_cost_summary(db_session, str(project.id))
    assert summary.task_count == 2
    assert summary.status_counts == {"completed": 1, "failed": 1}
    assert summary.actual_total == 3.0
    assert summary.estimated_total == 4.0
    assert summary.storage_bytes == 1000
