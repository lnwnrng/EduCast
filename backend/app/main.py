"""课影 EduCast — FastAPI 应用入口。"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import init_db
from app.exceptions import register_exception_handlers

logger = logging.getLogger(__name__)

# 全局共享的密码哈希上下文（供 auth_service 和 main 统一使用）
from passlib.context import CryptContext  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_sqlite_path() -> str:
    """从 SQLAlchemy engine URL 中提取 SQLite 数据库文件路径。"""
    from app.database import engine
    db_url = str(engine.url).replace("sqlite+aiosqlite:///", "")
    if db_url.startswith("/"):
        return db_url[1:]
    elif db_url.startswith("./"):
        return db_url[2:]
    return db_url


async def _seed_default_admin() -> None:
    """若无管理员账号，创建默认管理员 admin / admin123456。"""
    from app.database import async_session_factory
    from app.models.user import User

    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(User.role == "admin")
        )
        if result.scalar_one_or_none() is None:
            admin = User(
                username="admin",
                password_hash=pwd_context.hash("admin123456"),
                role="admin",
                display_id=1,
            )
            db.add(admin)
            await db.commit()


async def _migrate_add_display_id_column() -> None:
    """为已有 users 表添加 display_id 列并分配递增 ID。"""
    import logging
    import sqlite3

    logger = logging.getLogger(__name__)
    try:
        db_path = _get_sqlite_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "display_id" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN display_id INTEGER")
            # admin 始终为 display_id=1
            conn.execute(
                "UPDATE users SET display_id = 1 WHERE role = 'admin'"
            )
            # 其他用户按 created_at 顺序分配递增 ID
            conn.execute("""
                UPDATE users SET display_id = (
                    SELECT COUNT(*) + 1 FROM users AS u2
                    WHERE u2.created_at < users.created_at
                    AND u2.display_id IS NOT NULL
                )
                WHERE display_id IS NULL AND role != 'admin'
            """)
            # 如果还有 NULL（created_at 相同的情况），按 rowid 补充分配
            max_row = conn.execute(
                "SELECT COALESCE(MAX(display_id), 0) FROM users"
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT id FROM users WHERE display_id IS NULL ORDER BY created_at"
            ).fetchall()
            for i, row in enumerate(rows, start=max_row + 1):
                conn.execute(
                    "UPDATE users SET display_id = ? WHERE id = ?", (i, row[0])
                )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_display_id ON users(display_id)"
            )
            conn.commit()
            logger.info("已为 users 表添加 display_id 列")
        conn.close()
    except Exception as e:
        logger.warning("迁移 users.display_id 列失败（可忽略）: %s", e)


async def _migrate_add_email_column() -> None:
    """为已有 users 表添加 email 列（SQLite create_all 不会自动加列）。"""
    import logging
    import sqlite3

    logger = logging.getLogger(__name__)
    try:
        db_path = _get_sqlite_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "email" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)"
            )
            conn.commit()
            logger.info("已为 users 表添加 email 列")
        conn.close()
    except Exception as e:
        logger.warning("迁移 users.email 列失败（可忽略）: %s", e)


async def _migrate_add_template_column() -> None:
    """为已有 projects 表添加 template 列（视频模板功能所需）。"""
    import logging
    import sqlite3

    logger = logging.getLogger(__name__)
    try:
        db_path = _get_sqlite_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(projects)")
        columns = [row[1] for row in cursor.fetchall()]
        if "template" not in columns:
            conn.execute(
                "ALTER TABLE projects ADD COLUMN template VARCHAR(50) "
                "DEFAULT 'micro_lecture'"
            )
            conn.commit()
            logger.info("已为 projects 表添加 template 列")
        conn.close()
    except Exception as e:
        logger.warning("迁移 projects.template 列失败（可忽略）: %s", e)



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理。"""
    # ── 启动 ─────────────────────────────────────────────
    # P0: JWT 密钥安全检查 — 空值或默认值时拒绝启动
    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "":
        raise RuntimeError(
            "安全配置错误: JWT_SECRET_KEY 未设置。"
            "请在 .env 文件中配置一个强随机密钥后再启动。"
        )
    logger.info("JWT_SECRET_KEY 已配置，长度=%d", len(settings.JWT_SECRET_KEY))

    await init_db()
    await _migrate_add_email_column()
    await _migrate_add_display_id_column()
    await _migrate_add_template_column()
    await _seed_default_admin()
    os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
    yield
    # ── 关闭 ─────────────────────────────────────────────


app = FastAPI(
    title="课影 EduCast API",
    description="面向高校教学的智能视频生产平台",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 全局限速中间件 ─────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    from slowapi.middleware import SlowAPIMiddleware

    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)
    logger.info("全局限速已启用: 200 请求/分钟/IP")
except ImportError:
    logger.warning("slowapi 未安装，跳过全局限速 (pip install slowapi)")
    limiter = None  # type: ignore[assignment]

# ── 请求级结构化日志中间件 ─────────────────────────────────
from app.middleware.access_log import AccessLogMiddleware  # noqa: E402

app.add_middleware(AccessLogMiddleware)

# ── 异常处理器 ───────────────────────────────────────────
register_exception_handlers(app)

# ── 路由 ─────────────────────────────────────────────────
from app.api.v1 import api_v1_router  # noqa: E402

app.include_router(api_v1_router)

from app.api.v1.admin import admin_router  # noqa: E402

app.include_router(admin_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """根端点 — 健康检查。"""
    return {"message": "课影 EduCast API", "version": "0.1.0"}
