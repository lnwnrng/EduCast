# 用户系统设计文档

## 概述

为 EduCast 添加完整的用户认证与授权系统，包含管理员和普通用户两种角色，采用企业级 JWT 双 Token + httpOnly Cookie 方案。

## 数据模型

### User
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | |
| username | str(unique) | 3-32字符，字母数字下划线 |
| password_hash | str | bcrypt |
| role | enum("admin", "user") | 默认 "user" |
| is_active | bool | 默认 True |
| last_login | datetime | nullable |
| created_at | datetime | |
| updated_at | datetime | |

### RefreshToken
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | |
| user_id | int FK | → User |
| token_hash | str | sha256(token) |
| device_info | str | nullable，User-Agent |
| ip_address | str | nullable |
| expires_at | datetime | |
| is_revoked | bool | 默认 False |
| created_at | datetime | |

### AuditLog
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | |
| user_id | int FK | → User |
| action | str | "login", "register", "role_change" 等 |
| target_type | str | nullable，"user"/"project"/"task" |
| target_id | int | nullable |
| details | json | nullable |
| created_at | datetime | |

### Project 修改
- 新增字段 `user_id: int FK → User`

## 后端 API

### 认证接口 `/api/v1/auth/`
- POST `/register` — 注册，限流 10次/分钟
- POST `/login` — 登录，设置 httpOnly Cookie，限流 5次/分钟
- POST `/refresh` — 刷新 access token，Token 轮换
- POST `/logout` — 登出，撤销 refresh token
- GET `/me` — 获取当前用户

### 管理接口 `/api/v1/admin/`
- GET `/users` — 用户列表（分页+搜索+筛选）
- PATCH `/users/:id/role` — 修改角色
- PATCH `/users/:id/toggle-active` — 启用/禁用
- DELETE `/users/:id` — 删除用户
- GET `/logs` — 审计日志（分页+筛选）

### 项目接口改动
- GET `/projects` — 普通用户只返回自己的，admin 全部
- POST `/projects` — 自动绑定当前 user_id
- 各操作验证 owner 权限

## 安全方案

- **双 Token**: Access Token 15分钟，Refresh Token 7天
- **Token 轮换**: 每次刷新生成新 Refresh Token，旧 Token 作废
- **Cookie**: httpOnly + SameSite=Lax，Refresh Token 限定 Path=/api/v1/auth
- **密码**: bcrypt + 最少8位校验
- **限流**: 登录 5次/分钟，注册 10次/分钟
- **CSRF**: SameSite=Lax + 关键操作 Token 校验

## 前端架构

### 路由
- `/login` `/register` — 独立布局（无侧边栏）
- `/*` — ProtectedRoute → AppLayout → 原页面
- `/admin/users` `/admin/logs` — 仅 admin 可见

### 组件
- `ProtectedRoute` — 路由守卫，检查认证+角色
- `stores/authStore` — Zustand，存用户信息（不存 token）
- `api/client.ts` — Axios 401 拦截器自动刷新

### UI 风格
- 与现有 Ant Design 6 主题一致：浅蓝渐变背景，白色圆角卡片
- 侧边栏动态菜单（admin 显示用户管理+审计日志）
- Header 右侧添加用户头像下拉菜单

## 受影响文件

**后端新增**: models/user.py, models/refresh_token.py, models/audit_log.py, schemas/user.py, schemas/auth.py, api/v1/auth.py, api/v1/admin/__init__.py, api/v1/admin/users.py, services/auth_service.py, middleware/auth.py

**后端修改**: models/base.py, models/project.py, api/v1/projects.py, api/v1/__init__.py, main.py, config.py

**前端新增**: pages/Login/index.tsx, pages/Register/index.tsx, pages/Admin/UserManagement.tsx, pages/Admin/AuditLog.tsx, components/Auth/ProtectedRoute.tsx, stores/authStore.ts, api/auth.ts

**前端修改**: App.tsx, api/client.ts, components/Layout/AppLayout.tsx, types/ (新增 user.ts)