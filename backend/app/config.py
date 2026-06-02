"""应用配置管理 — 基于 Pydantic Settings。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """EduCast 全局配置。

    所有配置项可通过环境变量或 .env 文件覆盖。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── 数据库 ──────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./educast.db"

    # ── 存储 ────────────────────────────────────────────────
    STORAGE_ROOT: str = "./storage"

    # ── Provider API Keys ──────────────────────────────────
    ZHIPU_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    COGVIDEO_API_KEY: str = ""
    DIGITAL_HUMAN_API_KEY: str = ""

    # ── LLM（智谱 GLM）──────────────────────────────────────
    ZHIPU_MODEL: str = "glm-4.7-flash"
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    LLM_TIMEOUT: float = 60.0

    # ── TTS ─────────────────────────────────────────────────
    EDGE_TTS_VOICE: str = "zh-CN-XiaoxiaoNeural"

    # ── Provider 路由 ──────────────────────────────────────
    DEFAULT_ROUTING_STRATEGY: str = "free_first"

    # ── 成本护栏 ────────────────────────────────────────────
    MAX_COST_PER_TASK: float = 10.0
    MAX_COST_PER_PROJECT: float = 100.0

    # ── CORS ────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


settings = Settings()
