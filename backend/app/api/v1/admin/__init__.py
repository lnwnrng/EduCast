"""Admin API 路由聚合。"""

from fastapi import APIRouter, Depends

from app.api.v1.admin.users import router as users_router
from app.middleware.auth import require_admin

admin_router = APIRouter(
    prefix="/admin",
    tags=["管理员"],
    dependencies=[Depends(require_admin)],
)

admin_router.include_router(users_router)
