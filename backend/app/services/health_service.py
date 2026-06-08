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
    async def check_providers() -> HealthStatus:
        try:
            from app.providers.llm import get_llm_provider
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
            await HealthService.check_providers(),
            await HealthService.check_database(db),
        ]
        return [{"name": r.name, "status": r.status, "detail": r.detail} for r in results]