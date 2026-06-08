"""分类管理 API。"""

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


async def _count_projects(node: dict, db: AsyncSession) -> int:
    pc = await db.execute(
        select(func.count()).select_from(
            select(Project).where(Project.category_id == node["id"]).subquery()
        )
    )
    node["project_count"] = pc.scalar() or 0
    for child in node["children"]:
        node["project_count"] += await _count_projects(child, db)
    return node["project_count"]


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

    for item in tree:
        await _count_projects(item, db)

    return [CategoryNode(**item) for item in tree]


@router.post("/", response_model=CategoryNode, status_code=201, dependencies=[Depends(require_admin)])
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> CategoryNode:
    """创建分类（仅管理员）。"""
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
    result = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "分类不存在")
    if data.name is not None:
        cat.name = data.name
    if data.parent_id is not None:
        cat.parent_id = data.parent_id
    if data.sort_order is not None:
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
    children = await db.execute(
        select(CourseCategory).where(CourseCategory.parent_id == category_id)
    )
    if children.scalar_one_or_none():
        raise HTTPException(400, "该分类下有子分类，无法删除")

    proj = await db.execute(
        select(Project).where(Project.category_id == category_id).limit(1)
    )
    if proj.scalar_one_or_none():
        raise HTTPException(400, "该分类下有项目关联，无法删除")

    result = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "分类不存在")
    await db.delete(cat)
    return {"message": "分类已删除"}