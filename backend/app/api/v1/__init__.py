"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.api.v1.annotations import router as annotations_router
from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.llm_providers import router as llm_providers_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.projects import router as projects_router
from app.api.v1.requests import router as requests_router
from app.api.v1.resources import router as resources_router
from app.api.v1.scripts import router as scripts_router
from app.api.v1.settings import router as settings_router
from app.api.v1.tags import router as tags_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.upload import router as upload_router
from app.api.v1.video_gen_providers import router as video_gen_providers_router
from app.api.v1.websocket import router as ws_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(annotations_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(tags_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(resources_router)
api_v1_router.include_router(upload_router)
api_v1_router.include_router(scripts_router)
api_v1_router.include_router(monitoring_router)
api_v1_router.include_router(requests_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(llm_providers_router)
api_v1_router.include_router(video_gen_providers_router)
api_v1_router.include_router(ws_router)
