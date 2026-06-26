"""项目管理 API。"""

import json
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.config import Settings
from app.exceptions import ResourceNotFoundException, ValidationException
from app.ir.schema import CourseIR
from app.middleware.auth import get_current_user_from_cookie
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.parser_service import ParserService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["项目管理"])


def _check_project_access(project, current_user: User):
    """确保用户有权访问项目。"""
    if current_user.role != "admin" and str(project.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="项目不存在")


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> ProjectResponse:
    """创建新项目。"""
    project = await ProjectService.create_project(db, data, current_user.id)
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tag_ids: str | None = Query(None, description="标签ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> PaginatedResponse[ProjectResponse]:
    """分页查询项目列表。"""
    is_admin = current_user.role == "admin"
    tag_id_list = (
        [t.strip() for t in tag_ids.split(",") if t.strip()] if tag_ids else None
    )
    projects, total = await ProjectService.list_projects(
        db,
        page,
        page_size,
        user_id=current_user.id,
        is_admin=is_admin,
        tag_ids=tag_id_list,
    )
    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/analytics", response_model=SuccessResponse)
async def global_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """全局学情分析 — 跨项目汇总统计。"""
    from sqlalchemy import func, select

    from app.models.resource import Resource
    from app.models.task import Task

    # 权限过滤: admin 看全部，普通用户只看自己的项目
    project_filter = [Project.deleted_at.is_(None)]
    if current_user.role != "admin":
        project_filter.append(Project.user_id == current_user.id)

    # 项目总数
    project_count = (
        await db.execute(select(func.count(Project.id)).where(*project_filter))
    ).scalar() or 0

    # 可见项目 ID 列表
    visible_project_ids = (
        (await db.execute(select(Project.id).where(*project_filter))).scalars().all()
    )

    # 任务统计
    task_stmt = (
        select(Task)
        .where(
            Task.project_id.in_(visible_project_ids),
            Task.deleted_at.is_(None),
        )
        .order_by(Task.created_at.desc())
    )
    tasks = (await db.execute(task_stmt)).scalars().all()

    status_counts: dict[str, int] = {}
    total_estimated = 0.0
    total_actual = 0.0
    for t in tasks:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
        total_estimated += t.estimated_cost
        total_actual += t.actual_cost

    # 资源统计
    res_count = (
        await db.execute(
            select(func.count(Resource.id)).where(
                Resource.project_id.in_(visible_project_ids),
                Resource.deleted_at.is_(None),
            )
        )
    ).scalar() or 0

    video_count = (
        await db.execute(
            select(func.count(Resource.id)).where(
                Resource.project_id.in_(visible_project_ids),
                Resource.resource_type == "video",
                Resource.deleted_at.is_(None),
            )
        )
    ).scalar() or 0

    return SuccessResponse(
        message="全局学情分析数据",
        data={
            "project_count": project_count,
            "task_count": len(tasks),
            "status_counts": status_counts,
            "total_estimated_cost": round(total_estimated, 4),
            "total_actual_cost": round(total_actual, 4),
            "resource_count": res_count,
            "video_count": video_count,
            "recent_tasks": [
                {
                    "id": str(t.id),
                    "task_type": t.task_type,
                    "status": t.status,
                    "progress": t.progress,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks[:10]
            ],
        },
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> ProjectResponse:
    """获取项目详情。"""
    project = await ProjectService.get_project(db, project_id)
    _check_project_access(project, current_user)
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> ProjectResponse:
    """更新项目信息。"""
    project = await ProjectService.get_project(db, project_id)
    _check_project_access(project, current_user)
    project = await ProjectService.update_project(db, project_id, data)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """软删除项目。"""
    project = await ProjectService.get_project(db, project_id)
    _check_project_access(project, current_user)
    await ProjectService.delete_project(db, project_id)
    return SuccessResponse(message="项目已删除")


@router.get("/{project_id}/knowledge-graph")
async def get_knowledge_graph(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    """从 IR 提取知识点构建知识图谱数据。"""
    project = await ProjectService.get_project(db, project_id)
    _check_project_access(project, current_user)

    ir = await ParserService().load_ir(str(project_id))
    if ir is None:
        return {"nodes": [], "edges": []}
    return build_knowledge_graph(ir)


def build_knowledge_graph(ir: CourseIR) -> dict:
    """从 IR 构建知识图谱的节点与连边（纯函数，便于单测）。

    连边避免「同标签两两全连通」的 O(n²) 蛛网：章节相邻知识点顺承连边，
    具体标签把共享它的知识点串成链（跳过关联过多的泛标签），共享越多边权越高，
    去重并限制总边数。
    """
    nodes = []
    tag_to_kps: dict[str, list[str]] = defaultdict(list)
    chapter_kp_ids: list[list[str]] = []

    for chapter in ir.chapters:
        kp_ids: list[str] = []
        for kp in chapter.knowledge_points:
            nodes.append(
                {
                    "id": kp.kp_id,
                    "title": kp.title,
                    "chapter": chapter.title,
                    "chapter_order": chapter.order,
                    "tags": kp.tags or [],
                    "key_points": kp.key_points or [],
                }
            )
            kp_ids.append(kp.kp_id)
            for tag in kp.tags or []:
                tag_to_kps[tag].append(kp.kp_id)
        chapter_kp_ids.append(kp_ids)

    # 连边策略（避免「同标签两两全连通」的 O(n²) 蛛网）：
    #   1. 结构骨架：同章节相邻知识点顺承连边；
    #   2. 语义连边：仅对「具体标签」把共享它的知识点串成链（m-1 条而非 m(m-1)/2）；
    #      跳过关联过多知识点的泛标签（如学科名），它们只会把图连成一团；
    #   3. 共享越多边权越高，去重并限制总边数。
    edge_map: dict[tuple[str, str], dict] = {}

    def _add_edge(a: str, b: str, tag: str) -> None:
        if a == b:
            return
        key = (a, b) if a < b else (b, a)
        existing = edge_map.get(key)
        if existing:
            existing["weight"] += 1
        else:
            edge_map[key] = {
                "source": key[0],
                "target": key[1],
                "tag": tag,
                "weight": 1,
            }

    for kp_ids in chapter_kp_ids:
        for a, b in zip(kp_ids, kp_ids[1:]):
            _add_edge(a, b, "章节顺承")

    tag_cap = max(6, int(len(nodes) * 0.4))  # 关联超过此数的泛标签不连
    for tag, kp_ids in tag_to_kps.items():
        uniq = list(dict.fromkeys(kp_ids))  # 去重保序
        if len(uniq) < 2 or len(uniq) > tag_cap:
            continue
        for a, b in zip(uniq, uniq[1:]):
            _add_edge(a, b, tag)

    edges = list(edge_map.values())
    max_edges = 120
    if len(edges) > max_edges:
        edges.sort(key=lambda e: e["weight"], reverse=True)
        edges = edges[:max_edges]

    return {"nodes": nodes, "edges": edges}


@router.get("/{project_id}/assessment")
async def get_assessment(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    """从 IR 提取随堂练习题，按章节分组。"""
    project = await ProjectService.get_project(db, project_id)
    _check_project_access(project, current_user)

    ir = await ParserService().load_ir(str(project_id))
    if ir is None:
        return {"chapters": []}

    chapters = []
    for chapter in ir.chapters:
        questions = []
        for kp in chapter.knowledge_points:
            for qs in kp.quiz_seeds or []:
                questions.append(
                    {
                        "kp_id": kp.kp_id,
                        "kp_title": kp.title,
                        "question": qs.question,
                        "question_type": qs.question_type or "short",
                        "answer": qs.answer or "",
                        "explanation": qs.explanation or "",
                    }
                )
        if questions:
            chapters.append(
                {
                    "chapter_id": chapter.chapter_id,
                    "title": chapter.title,
                    "questions": questions,
                }
            )

    return {"chapters": chapters}


@router.get("/{project_id}/versions/compare")
async def compare_versions(
    project_id: UUID,
    v1: int = Query(..., description="版本 1"),
    v2: int = Query(..., description="版本 2"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user_from_cookie),
):
    """对比两个版本的 IR 差异。"""
    project = await ProjectService.get_project(db, project_id)
    _check_project_access(project, current_user)

    import json
    import os

    root = settings.STORAGE_ROOT
    ir_dir = os.path.join(root, str(project_id), "ir")

    def _load_ir(version: int):
        path = os.path.join(ir_dir, f"v{version}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    ir1 = _load_ir(v1)
    ir2 = _load_ir(v2)

    if ir1 is None or ir2 is None:
        return {"error": f"版本 {v1} 或 {v2} 的 IR 不存在"}

    # 提取知识点映射
    def _kp_map(ir_data):
        result = {}
        for ch in ir_data.get("chapters", []):
            for kp in ch.get("knowledge_points", []):
                result[kp.get("kp_id", "")] = {
                    "title": kp.get("title", ""),
                    "chapter": ch.get("title", ""),
                    "key_points": kp.get("key_points", []),
                    "tags": kp.get("tags", []),
                    "scene_count": len(kp.get("scenes", [])),
                }
        return result

    map1 = _kp_map(ir1)
    map2 = _kp_map(ir2)
    ids1 = set(map1.keys())
    ids2 = set(map2.keys())

    added = [{"id": kid, **map2[kid]} for kid in sorted(ids2 - ids1)]
    removed = [{"id": kid, **map1[kid]} for kid in sorted(ids1 - ids2)]
    modified = []
    for kid in sorted(ids1 & ids2):
        kp1, kp2 = map1[kid], map2[kid]
        changes = []
        if kp1["title"] != kp2["title"]:
            changes.append(f"标题: {kp1['title']} → {kp2['title']}")
        if kp1["scene_count"] != kp2["scene_count"]:
            changes.append(f"分镜数: {kp1['scene_count']} → {kp2['scene_count']}")
        if set(kp1.get("tags", [])) != set(kp2.get("tags", [])):
            changes.append("标签已变更")
        if changes:
            modified.append({"id": kid, "title": kp2["title"], "changes": changes})

    return {
        "v1": v1,
        "v2": v2,
        "chapter_count": {
            "v1": len(ir1.get("chapters", [])),
            "v2": len(ir2.get("chapters", [])),
        },
        "kp_count": {"v1": len(map1), "v2": len(map2)},
        "added": added,
        "removed": removed,
        "modified": modified,
        "summary": (
            f"新增 {len(added)} 个、删除 {len(removed)} 个、"
            f"修改 {len(modified)} 个知识点"
        ),
    }


# ── 视频片段重新生成 ──────────────────────────────────────


@router.post("/{project_id}/regenerate-scene", response_model=SuccessResponse)
async def regenerate_scene(
    project_id: UUID,
    scene_id: str = Query(..., description="要重新生成的分镜 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """重新生成指定分镜的视频片段。

    只重新渲染指定分镜的音频 + 画面，然后重新合成该分镜对应的视频片段，
    不影响其他分镜。合成后更新最终视频的对应时间段。
    """
    project = await db.get(Project, project_id)
    if not project:
        raise ResourceNotFoundException("项目不存在")
    _check_project_access(project, current_user)

    if project.status not in ("completed", "failed"):
        raise ValidationException("只能在已完成或失败的项目上重新生成分镜")

    # 加载 IR 并检查 scene_id 是否存在
    ir = await ParserService().load_ir(str(project_id))
    if ir is None:
        raise ResourceNotFoundException("未找到 IR 草稿")

    scene_exists = any(
        scene.scene_id == scene_id
        for chapter in ir.chapters
        for kp in chapter.knowledge_points
        for scene in kp.scenes
    )

    if not scene_exists:
        raise ResourceNotFoundException(f"分镜 {scene_id} 不存在")

    # 创建重新生成任务
    from app.models.task import Task

    task = Task(
        project_id=project_id,
        task_type="scene_regenerate",
        status="pending",
        config_json=json.dumps({"scene_id": scene_id}),
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    project.status = "generating"
    await db.commit()

    return SuccessResponse(
        message=f"分镜 {scene_id} 重新生成任务已创建",
        data={"task_id": str(task.id), "scene_id": scene_id},
    )


# ── 学情分析看板 ────────────────────────────────────────────


@router.get("/{project_id}/analytics", response_model=SuccessResponse)
async def project_analytics(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """项目学情分析看板 — 任务历史、成本汇总、资源统计。"""
    from sqlalchemy import func, select

    from app.models.annotation import Annotation
    from app.models.resource import Resource
    from app.models.task import Task

    project = await db.get(Project, project_id)
    if not project:
        raise ResourceNotFoundException("项目不存在")
    _check_project_access(project, current_user)

    # 任务统计（过滤软删除任务）
    task_stmt = (
        select(Task)
        .where(
            Task.project_id == project_id,
            Task.deleted_at.is_(None),
        )
        .order_by(Task.created_at.desc())
    )
    tasks_result = await db.execute(task_stmt)
    tasks = tasks_result.scalars().all()

    status_counts: dict[str, int] = {}
    total_estimated = 0.0
    total_actual = 0.0
    for t in tasks:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
        total_estimated += t.estimated_cost
        total_actual += t.actual_cost

    # 资源统计
    res_stmt = select(
        func.count(Resource.id),
        func.coalesce(func.sum(Resource.file_size), 0),
    ).where(
        Resource.project_id == project_id,
        Resource.deleted_at.is_(None),
    )
    res_count, storage_bytes = (await db.execute(res_stmt)).one()

    video_stmt = select(func.count(Resource.id)).where(
        Resource.project_id == project_id,
        Resource.resource_type == "video",
        Resource.deleted_at.is_(None),
    )
    video_count = (await db.execute(video_stmt)).scalar() or 0

    # 标注统计
    ann_stmt = select(func.count(Annotation.id)).where(
        Annotation.project_id == project_id,
        Annotation.deleted_at.is_(None),
    )
    annotation_count = (await db.execute(ann_stmt)).scalar() or 0

    return SuccessResponse(
        message="学情分析数据",
        data={
            "project_id": str(project_id),
            "task_count": len(tasks),
            "status_counts": status_counts,
            "total_estimated_cost": round(total_estimated, 4),
            "total_actual_cost": round(total_actual, 4),
            "resource_count": res_count,
            "video_count": video_count,
            "storage_bytes": storage_bytes,
            "annotation_count": annotation_count,
            "recent_tasks": [
                {
                    "id": str(t.id),
                    "task_type": t.task_type,
                    "status": t.status,
                    "progress": t.progress,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks[:10]
            ],
        },
    )
