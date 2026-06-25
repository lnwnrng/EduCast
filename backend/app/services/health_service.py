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
    async def check_providers(db=None) -> HealthStatus:
        """检查 LLM provider 可用情况（基于 DB 配置，回退 env ZHIPU）。"""
        try:
            from app.providers.llm import get_llm_providers_for_stages

            stage_map = await get_llm_providers_for_stages(db)
            providers = stage_map.get("default") or []
            if providers:
                names = ", ".join(
                    sorted({getattr(p, "provider_name", "?") for p in providers})
                )
                return HealthStatus(
                    name="LLM Provider",
                    status=True,
                    detail=f"{len(providers)} 个可用 ({names})",
                )
            return HealthStatus(
                name="LLM Provider", status=False, detail="未配置任何 LLM provider"
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
            await HealthService.check_providers(db),
            await HealthService.check_database(db),
        ]
        return [
            {"name": r.name, "status": r.status, "detail": r.detail} for r in results
        ]
