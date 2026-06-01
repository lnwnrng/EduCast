"""课影 EduCast — FastAPI 应用入口。"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理。"""
    # ── 启动 ─────────────────────────────────────────────
    await init_db()
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


@app.get("/")
async def root() -> dict[str, str]:
    """根端点 — 健康检查。"""
    return {"message": "课影 EduCast API", "version": "0.1.0"}
