"""SKIP_REVIEW 一键全自动测试 — 验证接线（不重测合成本身）。"""

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.v1 import upload as upload_module
from app.config import settings
from app.models.project import Project
from app.models.task import Task
from app.services.composition_service import CompositionService


async def _seed_and_run(async_engine, tmp_path, monkeypatch, *, skip_review: bool):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")  # 无 LLM → 本地降级，不触网
    monkeypatch.setattr(settings, "SKIP_REVIEW", skip_review)

    factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(upload_module, "async_session_factory", factory)

    spy = AsyncMock()
    monkeypatch.setattr(CompositionService, "compose", spy)

    md = tmp_path / "lesson.md"
    md.write_text("# 章\n## 知识点\n这是正文内容。\n", encoding="utf-8")

    async with factory() as db:
        project = Project(title="auto", status="parsing", user_id=uuid.uuid4())
        db.add(project)
        await db.flush()
        task = Task(project_id=project.id, task_type="full_pipeline", status="pending")
        db.add(task)
        await db.flush()
        await db.commit()
        pid, tid = str(project.id), str(task.id)

    await upload_module._run_parse_in_background(str(md), ".md", pid, tid)
    return spy


@pytest.mark.asyncio
async def test_skip_review_true_triggers_compose(
    async_engine, tmp_path, monkeypatch
) -> None:
    spy = await _seed_and_run(async_engine, tmp_path, monkeypatch, skip_review=True)
    spy.assert_awaited_once()


@pytest.mark.asyncio
async def test_skip_review_false_does_not_compose(
    async_engine, tmp_path, monkeypatch
) -> None:
    spy = await _seed_and_run(async_engine, tmp_path, monkeypatch, skip_review=False)
    spy.assert_not_awaited()
