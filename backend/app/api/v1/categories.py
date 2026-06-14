"""分类管理 API。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie, require_admin
from app.models.category import CourseCategory
from app.models.project import Project
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryNode, CategoryUpdate


def _build_tree(categories: list[CourseCategory]) -> list[dict]:
    mapping = {}
    for c in categories:
        mapping[str(c.id)] = {
            "id": str(c.id),
            "name": c.name,
            "parent_id": str(c.parent_id) if c.parent_id else None,
            "sort_order": c.sort_order,
            "children": [],
            "project_count": 0,
            "created_at": c.created_at,
        }
    items = list(mapping.values())
    tree = []
    for item in items:
        pid = item["parent_id"]
        if pid and pid in mapping:
            mapping[pid]["children"].append(item)
        else:
            tree.append(item)
    return tree


async def _fill_project_counts(tree: list[dict], db: AsyncSession) -> None:
    """批量查询所有分类的项目计数（一次性查询，避免 N+1）。"""
    # 收集所有分类 ID（含子节点）
    all_ids: list[uuid.UUID] = []

    def collect_ids(node: dict) -> None:
        all_ids.append(uuid.UUID(node["id"]))
        for child in node["children"]:
            collect_ids(child)

    for item in tree:
        collect_ids(item)

    if not all_ids:
        return

    # 一次性批量查询所有分类的项目数
    result = await db.execute(
        select(Project.category_id, func.count())
        .where(Project.category_id.in_(all_ids))
        .group_by(Project.category_id)
    )
    counts: dict[str, int] = {str(cid): cnt for cid, cnt in result.all()}

    def fill_node(node: dict) -> int:
        pc = counts.get(node["id"], 0)
        for child in node["children"]:
            pc += fill_node(child)
        node["project_count"] = pc
        return pc

    for item in tree:
        fill_node(item)


async def _check_duplicate_sort(
    db: AsyncSession, parent_id: str | None, sort_order: int, exclude_id: uuid.UUID | None = None,
) -> bool:
    """检查同级分类中是否存在重复的 sort_order。"""
    if parent_id:
        condition = CourseCategory.parent_id == parent_id
    else:
        condition = CourseCategory.parent_id.is_(None)
    query = select(CourseCategory).where(condition, CourseCategory.sort_order == sort_order)
    if exclude_id:
        query = query.where(CourseCategory.id != exclude_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


router = APIRouter(
    prefix="/categories",
    tags=["分类管理"],
)


@router.get("/", response_model=list[CategoryNode])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[CategoryNode]:
    """获取分类树（所有登录用户可读）。"""
    result = await db.execute(
        select(CourseCategory).order_by(CourseCategory.sort_order)
    )
    categories = list(result.scalars().all())
    tree = _build_tree(categories)

    await _fill_project_counts(tree, db)

    return [CategoryNode(**item) for item in tree]


@router.post("/", response_model=CategoryNode, status_code=201, dependencies=[Depends(require_admin)])
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> CategoryNode:
    """创建分类（仅管理员）。"""
    if await _check_duplicate_sort(db, data.parent_id, data.sort_order):
        raise HTTPException(400, "同级分类中已存在相同的排序号，请更换")
    cat = CourseCategory(
        name=data.name, parent_id=data.parent_id, sort_order=data.sort_order
    )
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return CategoryNode(
        id=str(cat.id), name=cat.name,
        parent_id=str(cat.parent_id) if cat.parent_id else None,
        sort_order=cat.sort_order, children=[], project_count=0,
        created_at=cat.created_at,
    )


@router.put("/{category_id}", response_model=CategoryNode, dependencies=[Depends(require_admin)])
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> CategoryNode:
    """更新分类（仅管理员）。"""
    cat_uuid = uuid.UUID(category_id)
    result = await db.execute(
        select(CourseCategory).where(CourseCategory.id == cat_uuid)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "分类不存在")
    if data.name is not None:
        cat.name = data.name
    if data.parent_id is not None:
        cat.parent_id = data.parent_id
    if data.sort_order is not None:
        target_parent = data.parent_id if data.parent_id is not None else cat.parent_id
        if await _check_duplicate_sort(db, target_parent, data.sort_order, exclude_id=cat_uuid):
            raise HTTPException(400, "同级分类中已存在相同的排序号，请更换")
        cat.sort_order = data.sort_order
    await db.flush()
    await db.refresh(cat)
    return CategoryNode(
        id=str(cat.id), name=cat.name,
        parent_id=str(cat.parent_id) if cat.parent_id else None,
        sort_order=cat.sort_order, children=[], project_count=0,
        created_at=cat.created_at,
    )


@router.delete("/{category_id}", dependencies=[Depends(require_admin)])
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> dict:
    """删除分类（有子分类或关联项目时禁止）。"""
    cat_uuid = uuid.UUID(category_id)
    children = await db.execute(
        select(CourseCategory).where(CourseCategory.parent_id == cat_uuid)
    )
    if children.scalar_one_or_none():
        raise HTTPException(400, "该分类下有子分类，无法删除")

    proj = await db.execute(
        select(Project).where(Project.category_id == cat_uuid).limit(1)
    )
    if proj.scalar_one_or_none():
        raise HTTPException(400, "该分类下有项目关联，无法删除")

    result = await db.execute(
        select(CourseCategory).where(CourseCategory.id == cat_uuid)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "分类不存在")
    await db.delete(cat)
    return {"message": "分类已删除"}
