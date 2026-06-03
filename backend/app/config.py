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

    # ── 生成式片段（智谱 CogVideoX，模块五）─────────────────────
    # CogVideoX 与 GLM 同平台；COGVIDEO_API_KEY 留空时回退用 ZHIPU_API_KEY
    COGVIDEO_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    COGVIDEO_MODEL: str = "cogvideox-flash"
    VIDEO_GEN_TIMEOUT: float = 300.0
    VIDEO_GEN_POLL_INTERVAL: float = 5.0

    # ── 数字人（模块四）─────────────────────────────────────
    # 本地兜底讲师画中画的姓名条文本；接入真机 API 后由 Provider 决定形象
    DIGITAL_HUMAN_AVATAR_NAME: str = "AI 讲师"

    # ── 公式动画（公式渲染画面）────────────────────────────────
    # auto: 探测到 manim+LaTeX 用 manim，否则降级图片显影; manim / image 可强制
    FORMULA_ENGINE: str = "auto"

    # ── TTS ─────────────────────────────────────────────────
    EDGE_TTS_VOICE: str = "zh-CN-XiaoxiaoNeural"

    # ── 视频合成（模块三）─────────────────────────────────────
    FFMPEG_BIN: str = "ffmpeg"
    FFPROBE_BIN: str = "ffprobe"
    VIDEO_WIDTH: int = 1920
    VIDEO_HEIGHT: int = 1080
    VIDEO_FPS: int = 30
    # 课件页渲染字体；留空则自动探测系统 CJK 字体（Windows 回退 msyh.ttc）
    SLIDE_FONT_PATH: str = ""
    # 可见水印文本；留空则使用课程标题
    WATERMARK_TEXT: str = ""
    # 分镜无旁白音频时的兜底时长（秒）
    SILENT_SCENE_DURATION: float = 4.0

    # ── Provider 路由 ──────────────────────────────────────
    DEFAULT_ROUTING_STRATEGY: str = "free_first"

    # ── 流水线 ──────────────────────────────────────────────
    # True 时上传后跨过人工审核，自动生成成片（演示用；默认保持人在环）
    SKIP_REVIEW: bool = False

    # ── 成本护栏 ────────────────────────────────────────────
    MAX_COST_PER_TASK: float = 10.0
    MAX_COST_PER_PROJECT: float = 100.0
    # 付费能力费率（元/秒）；用于生成前成本预估（真实 API 未接也给可信估值）
    DIGITAL_HUMAN_COST_PER_SEC: float = 0.5
    VIDEO_GEN_COST_PER_SEC: float = 1.0
    # 生成式片段默认时长（秒）与中文 TTS 估时长用的字/秒
    GEN_CLIP_SECONDS: float = 5.0
    TTS_CHARS_PER_SEC: float = 4.0

    # ── CORS ────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


settings = Settings()
