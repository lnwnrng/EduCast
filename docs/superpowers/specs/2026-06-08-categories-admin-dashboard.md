# 课件分类/标签与管理后台概览设计

## 概述

为 EduCast 增加课件分类与标签系统，同时增强监控面板为管理员总览页。

## 数据模型

### CourseCategory（树形分类）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| name | VARCHAR(100) | 分类名称 |
| parent_id | UUID FK nullable | 父分类，支持无限嵌套 |
| sort_order | INT | 同级排序 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### Tag（标签）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| name | VARCHAR(50) UNIQUE | 标签名 |
| color | VARCHAR(7) | 如 #1677ff |
| created_at | DATETIME | |

### Project 改动
- 新建 `project_id` ↔ `category_id` 多对一关系（一个项目一个分类）
- 新建 `project_tags` 中间表（项目 ↔ 标签多对多）
- 列表接口支持 category_id / tag_id 过滤

## 后端 API

### 分类接口 `/api/v1/categories/`
- GET `/` — 树形列表
- POST `/` — 创建
- PUT `/{id}` — 更新
- DELETE `/{id}` — 删除（有子分类或关联项目时禁止）

### 标签接口 `/api/v1/tags/`
- GET `/` — 列表
- POST `/` — 创建
- PUT `/{id}` — 更新名称/颜色
- DELETE `/{id}` — 删除

### 项目接口改动
- POST/PUT 支持 `category_id`, `tag_ids`
- GET 列表支持 `?category_id=&tag_id=` 过滤
- GET 详情返回 `category`, `tags`

### 监控接口增强
- `GET /monitoring/dashboard` — admin 额外返回用户数、注册趋势、存储用量
- `GET /monitoring/health` — 检查 FFmpeg、Provider、DB 状态

## 前端页面

### 后台管理（仅 admin）
- `/admin/categories` — 树形分类管理（TreeTable + Modal 编辑）
- `/admin/tags` — 标签列表管理（Table + 颜色选择器）

### 项目表单增强
- 创建/编辑项目：分类 Cascader + 标签多选 Select
- 项目列表：分类/标签筛选器

### 监控面板增强
- 管理员卡片行：用户数 / 注册 / 存储 / 健康状态
- 健康状态指示灯：FFmpeg / Provider / DB

## 受影响文件

**后端新增**: models/category.py, models/tag.py, schemas/category.py, schemas/tag.py, api/v1/categories.py, api/v1/tags.py

**后端修改**: models/project.py（多对多关系）, api/v1/projects.py（过滤+关联）, api/v1/__init__.py（注册路由）, api/v1/monitoring.py（管理数据）, services/project_service.py（分类标签支持）

**前端新增**: pages/Admin/CategoryManagement.tsx, pages/Admin/TagManagement.tsx, api/categories.ts, api/tags.ts

**前端修改**: App.tsx（添加 admin 路由）, components/Layout/AppLayout.tsx（菜单）, pages/Monitoring/index.tsx（增强面板）, pages/Projects/index.tsx（筛选器）, pages/Upload/index.tsx（分类+标签选择）, types/project.ts（扩展字段）