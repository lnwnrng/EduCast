---
name: python-backend
description: 当开发 EduCast 后端代码（Python/FastAPI/Celery/FFmpeg/manim）时使用此技能，定义了代码规范、架构约定和最佳实践。
---

# Python 后端开发规范 — 课影 (EduCast)

## 技术栈
- **语言**: Python 3.11+
- **Web 框架**: FastAPI（异步优先）
- **任务队列**: Celery + Redis（或 FastAPI BackgroundTasks 起步）
- **数据库**: SQLite（毕设）→ PostgreSQL（生产）
- **ORM**: SQLAlchemy 2.0+（async session）
- **媒体处理**: FFmpeg（核心）、MoviePy
- **公式动画**: manim（CPU 渲染）
- **文档解析**: python-pptx, PyMuPDF(fitz), pdfplumber, mammoth, Pillow
- **TTS**: Edge-TTS（免费首选）
- **LLM**: 智谱 GLM-4-Flash / DeepSeek

## 代码风格
- 遵循 **PEP 8**，行宽 88（Black 格式化）
- 使用 **Type Hints** 标注所有函数签名
- 使用 **Pydantic v2** 做数据校验与序列化
- 命名规范：
  - 变量/函数: `snake_case`
  - 类: `PascalCase`
  - 常量: `UPPER_SNAKE_CASE`
  - 私有方法: `_leading_underscore`

## 项目结构约定
```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 配置管理（Pydantic Settings）
│   ├── models/               # SQLAlchemy 模型
│   ├── schemas/              # Pydantic schemas（请求/响应）
│   ├── api/                  # API 路由
│   │   └── v1/
│   ├── services/             # 业务逻辑层
│   ├── providers/            # Provider 适配层（LLM/TTS/数字人/视频生成）
│   │   ├── base.py           # 抽象基类
│   │   ├── llm/
│   │   ├── tts/
│   │   ├── digital_human/
│   │   └── video_gen/
│   ├── pipeline/             # 任务流水线编排
│   │   ├── parser.py         # 文档解析
│   │   ├── scriptwriter.py   # 脚本编排
│   │   ├── renderer.py       # 课件渲染
│   │   ├── composer.py       # FFmpeg 合成
│   │   └── tasks.py          # Celery/Background 任务
│   ├── ir/                   # 课程脚本中间表示（IR/DSL）
│   │   ├── schema.py         # IR JSON Schema
│   │   └── validator.py
│   ├── storage/              # 存储抽象层
│   └── utils/
├── tests/
├── alembic/                  # 数据库迁移
└── pyproject.toml
```

## 架构原则
1. **薄模型、厚编排** — 不自训模型，价值在流水线编排
2. **Provider 适配层** — 所有外部 API 统一抽象接口，支持路由/降级/成本核算
3. **异步任务流水线** — 全流程任务化，支持重试/限流/幂等/断点续跑
4. **课件优先** — 课件渲染 + TTS 为主体画面，生成式视频仅点缀
5. **IR 驱动** — 课程脚本中间表示是系统枢纽，解析与生成通过 IR 解耦
6. **成本护栏** — 预算配额、单任务成本预估、缓存复用
7. **人在环** — 关键节点（脚本、分镜）可人工审核修改

## FastAPI 约定
- 路由使用 `APIRouter`，按模块分组
- 错误处理使用自定义异常 + 全局异常处理器
- 长任务返回 `task_id`，通过轮询/WebSocket 获取进度
- API 版本化：`/api/v1/`
- 使用 `Depends()` 做依赖注入（数据库会话、认证等）

## 数据库约定
- 所有表使用 UUID 主键
- 创建时间 `created_at`、更新时间 `updated_at` 必填
- 软删除使用 `deleted_at` 字段
- 数据库迁移使用 Alembic

## Provider 适配层约定
- 每个 Provider 实现统一接口（`submit` → `poll` → `get_result`）
- 支持降级链：首选 → 备选 → 最终降级（纯课件版本）
- 每次调用记录用量与费用
- 相同输入命中缓存直接复用

## 测试
- 使用 `pytest` + `pytest-asyncio`
- 单元测试覆盖 services 层
- 集成测试覆盖 API 端点
- Provider 测试使用 mock
