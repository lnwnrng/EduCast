"""课影 EduCast — FastAPI 应用入口。"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from sqlalchemy import select

from app.config import settings
from app.database import init_db
from app.exceptions import register_exception_handlers

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
            )
            db.add(admin)
            await db.commit()


async def _migrate_add_email_column() -> None:
    """为已有 users 表添加 email 列（SQLite create_all 不会自动加列）。"""
    import logging
    import sqlite3
    from app.database import engine

    logger = logging.getLogger(__name__)
    try:
        # 使用同步 sqlite3 直接执行，避免 async SQLAlchemy 的复杂性
        db_url = str(engine.url).replace("sqlite+aiosqlite:///", "")
        # 处理相对路径
        if db_url.startswith("/"):
            db_path = db_url[1:]  # 去掉前导 /
        elif db_url.startswith("./"):
            db_path = db_url[2:]
        else:
            db_path = db_url
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理。"""
    # ── 启动 ─────────────────────────────────────────────
    await init_db()
    await _migrate_add_email_column()
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
