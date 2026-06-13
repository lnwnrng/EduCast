"""项目管理 API。"""

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.config import Settings
from app.middleware.auth import get_current_user_from_cookie
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
    category_id: str | None = Query(None, description="分类ID"),
    tag_ids: str | None = Query(None, description="标签ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> PaginatedResponse[ProjectResponse]:
    """分页查询项目列表。"""
    is_admin = current_user.role == "admin"
    tag_id_list = [t.strip() for t in tag_ids.split(",") if t.strip()] if tag_ids else None
    projects, total = await ProjectService.list_projects(
        db, page, page_size,
        user_id=current_user.id,
        is_admin=is_admin,
        category_id=category_id,
        tag_ids=tag_id_list,
    )
    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
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

    nodes = []
    tag_to_kps: dict[str, list[str]] = defaultdict(list)

    for chapter in ir.chapters:
        for kp in chapter.knowledge_points:
            nodes.append({
                "id": kp.kp_id,
                "title": kp.title,
                "chapter": chapter.title,
                "chapter_order": chapter.order,
                "tags": kp.tags or [],
                "key_points": kp.key_points or [],
            })
            for tag in (kp.tags or []):
                tag_to_kps[tag].append(kp.kp_id)

    edges = []
    seen = set()
    for tag, kp_ids in tag_to_kps.items():
        for i in range(len(kp_ids)):
            for j in range(i + 1, len(kp_ids)):
                pair = tuple(sorted([kp_ids[i], kp_ids[j]]))
                if pair not in seen:
                    seen.add(pair)
                    edges.append({
                        "source": pair[0],
                        "target": pair[1],
                        "tag": tag,
                    })

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
            for qs in (kp.quiz_seeds or []):
                questions.append({
                    "kp_id": kp.kp_id,
                    "kp_title": kp.title,
                    "question": qs.question,
                    "question_type": qs.question_type or "short",
                    "answer": qs.answer or "",
                    "explanation": qs.explanation or "",
                })
        if questions:
            chapters.append({
                "chapter_id": chapter.chapter_id,
                "title": chapter.title,
                "questions": questions,
            })

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
        "summary": f"新增 {len(added)} 个、删除 {len(removed)} 个、修改 {len(modified)} 个知识点",
    }
