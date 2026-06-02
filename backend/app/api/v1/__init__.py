"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.projects import router as projects_router
from app.api.v1.resources import router as resources_router
from app.api.v1.scripts import router as scripts_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.upload import router as upload_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(projects_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(resources_router)
api_v1_router.include_router(upload_router)
api_v1_router.include_router(scripts_router)
api_v1_router.include_router(monitoring_router)
