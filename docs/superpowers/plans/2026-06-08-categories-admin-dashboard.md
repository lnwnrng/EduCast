# 课件分类/标签 + 管理后台概览 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add tree-based course categories, tag system, and enhanced admin monitoring dashboard.

**Architecture:** Backend: new CourseCategory (tree) and Tag (flat) models, M2M with Project, admin-only management APIs, health check endpoint. Frontend: tree table for categories, tag table with color picker, cascader in project forms, enhanced monitoring page with admin stats cards.

**Tech Stack:** Backend: SQLAlchemy tree queries (recursive CTE or parent-based), Pydantic nested serialization. Frontend: Ant Design Tree, Cascader, Tag color picker.

---

### Task 1: Backend — Category & Tag Models

**Files:**
- Create: `backend/app/models/category.py`
- Create: `backend/app/models/tag.py`
- Create: `backend/app/models/project_tag.py`
- Modify: `backend/app/models/project.py` — add category_id FK, tags relationship
- Modify: `backend/app/models/__init__.py` — export new models

- [ ] **Step 1: Create category.py**

```python
"""课程分类模型（树形结构）。"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.project import Project


class CourseCategory(BaseMixin, Base):
    """课程分类 — 支持无限级树形结构。"""

    __tablename__ = "course_categories"

    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("course_categories.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # ── 关系 ─────────────────────────────────────────────
    children: Mapped[list["CourseCategory"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent: Mapped["CourseCategory | None"] = relationship(
        back_populates="children", remote_side="CourseCategory.id"
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="category")
```

- [ ] **Step 2: Create tag.py**

```python
"""标签模型。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class Tag(BaseMixin, Base):
    """标签 — 自由打标。"""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#1677ff")
```

- [ ] **Step 3: Create project_tag.py** (关联表)

```python
"""项目-标签 多对多关联表。"""

from sqlalchemy import Column, ForeignKey, String, Table

from app.models.base import Base

project_tag = Table(
    "project_tags",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)
```

- [ ] **Step 4: Modify project.py**

Add to Project model:
```python
category_id: Mapped[str | None] = mapped_column(
    ForeignKey("course_categories.id"), nullable=True, default=None
)
category: Mapped["CourseCategory | None"] = relationship(back_populates="projects")
tags: Mapped[list["Tag"]] = relationship(secondary="project_tags")
```

Add TYPE_CHECKING imports for `CourseCategory` and `Tag`.

- [ ] **Step 5: Update `__init__.py`** — add import/export for CourseCategory, Tag, project_tag

- [ ] **Step 6: Rebuild DB and verify**

```bash
cd backend && rm -f educast.db && python -c "from app.database import init_db; import asyncio; asyncio.run(init_db()); print('OK')"
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/category.py backend/app/models/tag.py backend/app/models/project_tag.py backend/app/models/project.py backend/app/models/__init__.py
git commit -m "feat: add CourseCategory (tree), Tag, and project-tag M2M models"
```

---

### Task 2: Backend — Category & Tag Schemas + APIs

**Files:**
- Create: `backend/app/schemas/category.py`
- Create: `backend/app/schemas/tag.py`
- Create: `backend/app/api/v1/categories.py`
- Create: `backend/app/api/v1/tags.py`
- Modify: `backend/app/schemas/project.py` — add category/tag fields
- Modify: `backend/app/api/v1/projects.py` — add filter support
- Modify: `backend/app/api/v1/__init__.py` — register new routers
- Modify: `backend/app/services/project_service.py` — handle category/tag on create/update

- [ ] **Step 1: Create schemas**

**category.py:**
```python
from datetime import datetime
from pydantic import BaseModel


class CategoryNode(BaseModel):
    """分类节点（含子节点递归）。"""
    id: str
    name: str
    parent_id: str | None = None
    sort_order: int = 0
    children: list["CategoryNode"] = []
    project_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    parent_id: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    sort_order: int | None = None
```

**tag.py:**
```python
from datetime import datetime
from pydantic import BaseModel


class TagResponse(BaseModel):
    id: str
    name: str
    color: str = "#1677ff"
    project_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str
    color: str = "#1677ff"


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
```

- [ ] **Step 2: Create category API route**

```python
"""分类管理 API。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie, require_admin
from app.models.category import CourseCategory
from app.models.project import Project
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryNode, CategoryUpdate


def _build_tree(categories: list[CourseCategory]) -> list[dict]:
    """将扁平分类列表构建为树形结构。"""
    tree = []
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
    for item in items:
        if item["parent_id"] and item["parent_id"] in mapping:
            mapping[item["parent_id"]]["children"].append(item)
        else:
            tree.append(item)
    return tree


router = APIRouter(prefix="/categories", tags=["分类管理"],
                   dependencies=[Depends(require_admin)])


@router.get("/", response_model=list[CategoryNode])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[CategoryNode]:
    """获取分类树。"""
    result = await db.execute(
        select(CourseCategory).order_by(CourseCategory.sort_order)
    )
    categories = list(result.scalars().all())

    # 获取每个分类的项目数
    trees = _build_tree(categories)
    for item in trees:
        pc = await db.execute(
            select(func.count()).select_from(
                select(Project).where(Project.category_id == item["id"]).subquery()
            )
        )
        item["project_count"] = pc.scalar() or 0

    return [CategoryNode(**item) for item in trees]


@router.post("/", response_model=CategoryNode, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> CategoryNode:
    """创建分类。"""
    cat = CourseCategory(name=data.name, parent_id=data.parent_id, sort_order=data.sort_order)
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return CategoryNode(
        id=str(cat.id), name=cat.name, parent_id=str(cat.parent_id) if cat.parent_id else None,
        sort_order=cat.sort_order, children=[], project_count=0, created_at=cat.created_at,
    )


@router.put("/{category_id}", response_model=CategoryNode)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> CategoryNode:
    """更新分类。"""
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
        id=str(cat.id), name=cat.name, parent_id=str(cat.parent_id) if cat.parent_id else None,
        sort_order=cat.sort_order, children=[], project_count=0, created_at=cat.created_at,
    )


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> dict:
    """删除分类（有子分类或关联项目时禁止）。"""
    # 检查子分类
    children_result = await db.execute(
        select(CourseCategory).where(CourseCategory.parent_id == category_id)
    )
    if children_result.scalar_one_or_none():
        raise HTTPException(400, "该分类下有子分类，无法删除")

    # 检查关联项目
    proj_result = await db.execute(
        select(Project).where(Project.category_id == category_id).limit(1)
    )
    if proj_result.scalar_one_or_none():
        raise HTTPException(400, "该分类下有项目关联，无法删除")

    result = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "分类不存在")
    await db.delete(cat)
    return {"message": "分类已删除"}
```

- [ ] **Step 3: Create tag API route**

```python
"""标签管理 API。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie, require_admin
from app.models.project import project_tag
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagResponse, TagUpdate

router = APIRouter(prefix="/tags", tags=["标签管理"],
                   dependencies=[Depends(require_admin)])


@router.get("/", response_model=list[TagResponse])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[TagResponse]:
    """标签列表。"""
    result = await db.execute(select(Tag).order_by(Tag.name))
    tags = list(result.scalars().all())
    items = []
    for t in tags:
        pc = await db.execute(
            select(func.count()).select_from(
                select(project_tag).where(project_tag.c.tag_id == t.id).subquery()
            )
        )
        items.append(TagResponse(
            id=str(t.id), name=t.name, color=t.color,
            project_count=pc.scalar() or 0, created_at=t.created_at,
        ))
    return items


@router.post("/", response_model=TagResponse, status_code=201)
async def create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> TagResponse:
    """创建标签。"""
    tag = Tag(name=data.name, color=data.color)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return TagResponse(
        id=str(tag.id), name=tag.name, color=tag.color,
        project_count=0, created_at=tag.created_at,
    )


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    data: TagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> TagResponse:
    """更新标签。"""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(404, "标签不存在")
    if data.name is not None:
        tag.name = data.name
    if data.color is not None:
        tag.color = data.color
    await db.flush()
    await db.refresh(tag)
    return TagResponse(
        id=str(tag.id), name=tag.name, color=tag.color,
        project_count=0, created_at=tag.created_at,
    )


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> dict:
    """删除标签。"""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(404, "标签不存在")
    await db.delete(tag)
    return {"message": "标签已删除"}
```

- [ ] **Step 4: Update project schemas & service**

Add to `ProjectResponse`:
```python
category_id: str | None = None
category: CategoryNode | None = None
tags: list[TagResponse] = []
```

Modify `ProjectCreate`:
```python
category_id: str | None = None
tag_ids: list[str] = []
```

Modify `ProjectUpdate` similarly.

In `project_service.py`:
- `create_project`: accept `category_id` and `tag_ids`, set them on the project
- `update_project`: accept `category_id` and `tag_ids`, update them

- [ ] **Step 5: Update project list API — add filters**

Add query params to `GET /projects/`:
```python
category_id: str | None = Query(None),
tag_id: str | None = Query(None),
```

Filter by `Project.category_id == category_id` and/or join `project_tag` table when tag_id provided.

- [ ] **Step 6: Register new routers in `__init__.py`**

```python
from app.api.v1.categories import router as categories_router
from app.api.v1.tags import router as tags_router
api_v1_router.include_router(categories_router)
api_v1_router.include_router(tags_router)
```

- [ ] **Step 7: Verify**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/category.py backend/app/schemas/tag.py backend/app/api/v1/categories.py backend/app/api/v1/tags.py backend/app/schemas/project.py backend/app/api/v1/projects.py backend/app/api/v1/__init__.py backend/app/services/project_service.py
git commit -m "feat: add category/tag CRUD APIs and project filtering"
```

---

### Task 3: Backend — Enhanced Monitoring & Health Check

**Files:**
- Modify: `backend/app/api/v1/monitoring.py` — add admin stats + health check
- Create: `backend/app/services/health_service.py`

- [ ] **Step 1: Create health_service.py**

```python
"""系统健康检查服务。"""

import subprocess
from dataclasses import dataclass


@dataclass
class HealthStatus:
    name: str
    status: bool
    detail: str | None = None


class HealthService:

    @staticmethod
    def check_ffmpeg() -> HealthStatus:
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            version = result.stdout.split("\n")[0] if result.stdout else "unknown"
            return HealthStatus(name="FFmpeg", status=True, detail=version)
        except Exception as e:
            return HealthStatus(name="FFmpeg", status=False, detail=str(e))

    @staticmethod
    async def check_providers(db) -> HealthStatus:
        from app.providers.llm import get_llm_provider
        try:
            provider = get_llm_provider()
            return HealthStatus(
                name="LLM Provider", status=True,
                detail=f"{provider.__class__.__name__} configured",
            )
        except Exception as e:
            return HealthStatus(name="LLM Provider", status=False, detail=str(e))

    @staticmethod
    async def check_database(db) -> HealthStatus:
        try:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            return HealthStatus(name="Database", status=True)
        except Exception as e:
            return HealthStatus(name="Database", status=False, detail=str(e))

    @staticmethod
    async def run_all(db) -> list[dict]:
        results = [
            HealthService.check_ffmpeg(),
            await HealthService.check_providers(db),
            await HealthService.check_database(db),
        ]
        return [{"name": r.name, "status": r.status, "detail": r.detail} for r in results]
```

- [ ] **Step 2: Update monitoring.py**

Add to the dashboard endpoint — when current user is admin, append:
```python
# Admin-only stats
from app.models.user import User
from app.models.project import Project
from sqlalchemy import func, select

# Total users, today's registrations
user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
today_reg = (await db.execute(
    select(func.count(User.id)).where(
        func.date(User.created_at) == func.current_date()
    )
)).scalar() or 0
project_count = (await db.execute(
    select(func.count(Project.id)).where(Project.deleted_at.is_(None))
)).scalar() or 0

# Storage usage (approximate from resource files)
from app.models.resource import Resource
storage_result = await db.execute(
    select(func.coalesce(func.sum(Resource.file_size), 0))
)
storage_bytes = storage_result.scalar() or 0
```

Return admin data under `admin_stats` key.

Add a new endpoint:
```python
@router.get("/health", response_model=list)
async def system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    """系统健康检查（仅管理员）。"""
    from app.middleware.auth import require_admin
    await require_admin(current_user)
    return await HealthService.run_all(db)
```

- [ ] **Step 3: Verify**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/health_service.py backend/app/api/v1/monitoring.py
git commit -m "feat: add health check service and admin monitoring stats"
```

---

### Task 4: Frontend — Admin Category & Tag Pages

**Files:**
- Create: `frontend/src/api/categories.ts`
- Create: `frontend/src/api/tags.ts`
- Create: `frontend/src/pages/Admin/CategoryManagement.tsx`
- Create: `frontend/src/pages/Admin/TagManagement.tsx`
- Modify: `frontend/src/App.tsx` — add admin routes
- Modify: `frontend/src/components/Layout/AppLayout.tsx` — add menu items

- [ ] **Step 1: Create api/categories.ts**

```typescript
import apiClient from './client';

export interface CategoryNode {
  id: string;
  name: string;
  parent_id: string | null;
  sort_order: number;
  children: CategoryNode[];
  project_count: number;
  created_at: string;
}

export const getCategories = () =>
  apiClient.get<CategoryNode[]>('/categories/');

export const createCategory = (data: { name: string; parent_id?: string | null; sort_order?: number }) =>
  apiClient.post<CategoryNode>('/categories/', data);

export const updateCategory = (id: string, data: { name?: string; parent_id?: string | null; sort_order?: number }) =>
  apiClient.put<CategoryNode>(`/categories/${id}`, data);

export const deleteCategory = (id: string) =>
  apiClient.delete(`/categories/${id}`);
```

- [ ] **Step 2: Create api/tags.ts**

```typescript
import apiClient from './client';

export interface TagItem {
  id: string;
  name: string;
  color: string;
  project_count: number;
  created_at: string;
}

export const getTags = () =>
  apiClient.get<TagItem[]>('/tags/');

export const createTag = (data: { name: string; color?: string }) =>
  apiClient.post<TagItem>('/tags/', data);

export const updateTag = (id: string, data: { name?: string; color?: string }) =>
  apiClient.put<TagItem>(`/tags/${id}`, data);

export const deleteTag = (id: string) =>
  apiClient.delete(`/tags/${id}`);
```

- [ ] **Step 3: Create CategoryManagement.tsx**

Use Ant Design Table with `children` column to display tree. Include:
- "添加根分类" button at top
- Each row shows name + sort_order + project_count
- Actions: "添加子分类" / "编辑" / "删除"
- Edit/Create uses a Modal with name input and parent select

Key structure:
```tsx
import React, { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Space, Popconfirm, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import * as catApi from '../../api/categories';
import type { CategoryNode } from '../../api/categories';

const { Title } = Typography;

const CategoryManagement: React.FC = () => {
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CategoryNode | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await catApi.getCategories();
      setCategories(data);
    } catch { /* handled */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await catApi.updateCategory(editing.id, values);
        message.success('已更新');
      } else {
        await catApi.createCategory(values);
        message.success('已创建');
      }
      setModalOpen(false);
      fetchData();
    } catch { /* handled */ }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80 },
    { title: '项目数', dataIndex: 'project_count', key: 'project_count', width: 80 },
    {
      title: '操作', key: 'action', width: 240,
      render: (_: any, record: CategoryNode) => (
        <Space>
          <Button size="small" onClick={() => { setEditing(null); form.setFieldsValue({ parent_id: record.id, name: '', sort_order: 0 }); setModalOpen(true); }}>添加子分类</Button>
          <Button size="small" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true); }}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={async () => { await catApi.deleteCategory(record.id); message.success('已删除'); fetchData(); }}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4}>分类管理</Title>
      <Button icon={<PlusOutlined />} onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }} style={{ marginBottom: 16 }}>添加根分类</Button>
      <Table columns={columns} dataSource={categories} rowKey="id" loading={loading} pagination={false} />
      <Modal title={editing ? '编辑分类' : '新建分类'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="sort_order" label="排序"><InputNumber min={0} /></Form.Item>
          <Form.Item name="parent_id" label="父分类" hidden><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
export default CategoryManagement;
```

- [ ] **Step 4: Create TagManagement.tsx**

Similar structure but with Table + color input. Include color preview circle using `Tag` component from Ant Design.

- [ ] **Step 5: Update App.tsx**

Add routes inside the admin ProtectedRoute group:
```tsx
<Route path="/admin/categories" element={<CategoryManagement />} />
<Route path="/admin/tags" element={<TagManagement />} />
```

Add imports for the two new components.

- [ ] **Step 6: Update AppLayout.tsx sidebar**

Add menu items under the "管理" submenu:
```typescript
{ key: '/admin/categories', label: '分类管理' },
{ key: '/admin/tags', label: '标签管理' },
```

- [ ] **Step 7: Verify frontend compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/categories.ts frontend/src/api/tags.ts frontend/src/pages/Admin/CategoryManagement.tsx frontend/src/pages/Admin/TagManagement.tsx frontend/src/App.tsx frontend/src/components/Layout/AppLayout.tsx
git commit -m "feat: add admin category/tag management pages"
```

---

### Task 5: Frontend — Project Form Category/Tag Integration

**Files:**
- Modify: `frontend/src/pages/Projects/index.tsx` — add filters
- Modify: `frontend/src/pages/Upload/index.tsx` — add category/tag selectors
- Modify: `frontend/src/types/project.ts` — add category/tag fields
- Modify: `frontend/src/api/projects.ts` — add filter params

- [ ] **Step 1: Update types/project.ts**

```typescript
export interface Project {
  // ... existing fields
  category_id: string | null;
  category: { id: string; name: string } | null;
  tags: Array<{ id: string; name: string; color: string }>;
}

export interface ProjectCreate {
  // ... existing
  category_id?: string;
  tag_ids?: string[];
}

export interface ProjectUpdate {
  // ... existing
  category_id?: string | null;
  tag_ids?: string[];
}
```

- [ ] **Step 2: Update api/projects.ts**

Add filter params to `getProjects`:
```typescript
export const getProjects = (page = 1, pageSize = 20, params?: { category_id?: string; tag_id?: string }) =>
  apiClient.get<PaginatedResponse<Project>>('/projects/', {
    params: { page, page_size: pageSize, ...params },
  });
```

- [ ] **Step 3: Update Projects page**

Add filter bar above table: Category cascader + Tag multi-select. Fetch available categories/tags from their respective APIs.

- [ ] **Step 4: Update Upload/Create project page**

Add CategorySelect (Cascder) and TagSelect (Select mode="multiple") to the project creation form.

- [ ] **Step 5: Verify frontend compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/project.ts frontend/src/api/projects.ts frontend/src/pages/Projects/index.tsx frontend/src/pages/Upload/index.tsx
git commit -m "feat: integrate category/tag selectors into project forms and filters"
```

---

### Task 6: Frontend — Enhanced Monitoring Dashboard

**Files:**
- Modify: `frontend/src/pages/Monitoring/index.tsx` — add admin stats cards
- Modify: `frontend/src/api/monitoring.ts` — add health endpoint

- [ ] **Step 1: Update api/monitoring.ts**

Add:
```typescript
export const getHealth = () =>
  apiClient.get<Array<{ name: string; status: boolean; detail: string | null }>>('/monitoring/health');
```

- [ ] **Step 2: Update Monitoring page**

Above the existing content, add admin-only section (use `useAuthStore` to check role):
- Stats row: 4 cards (总用户数 / 今日注册 / 总项目数 / 存储用量)
- Health status row: 3 indicators with green/red dots

Wrap in `{user?.role === 'admin' && (...)}` to only show for admins.

- [ ] **Step 3: Verify frontend compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Monitoring/index.tsx frontend/src/api/monitoring.ts
git commit -m "feat: add admin stats and health check to monitoring page"
```

---

### Task 7: End-to-End Verification

- [ ] **Step 1: Restart backend and verify APIs**

```bash
cd backend && rm -f educast.db && python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Test with curl:
```bash
# Login as admin
curl -X POST .../auth/login -d '{"username":"admin","password":"admin123456}' -c cookies.txt

# Create category
curl -X POST .../categories/ -H "Content-Type: application/json" -b cookies.txt -d '{"name":"理工科"}'

# Get category tree
curl -s .../categories/ -b cookies.txt

# Create tag
curl -X POST .../tags/ -H "Content-Type: application/json" -b cookies.txt -d '{"name":"精品课","color":"#1677ff"}'

# Create project with category and tags
curl -X POST .../projects/ -H "Content-Type: application/json" -b cookies.txt \
  -d '{"title":"高数","category_id":"...","tag_ids":["..."]}'

# Health check
curl -s .../monitoring/health -b cookies.txt
```

- [ ] **Step 2: Start frontend and verify UI**

```bash
cd frontend && npx vite --port 5173
```

Check:
1. Admin sidebar shows 分类管理 / 标签管理
2. Can create/edit/delete categories in tree
3. Can create/edit/delete tags
4. Project form shows category + tag selectors
5. Project list filters by category/tag
6. Monitoring page shows admin stats when logged in as admin

- [ ] **Step 3: Commit any final fixes**

```bash
git commit -m "fix: post-verification adjustments"
```