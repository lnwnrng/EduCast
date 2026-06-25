"""LLM Provider 子包 — 多模型路由（cc-switch 风格）。

PROVIDER_REGISTRY 提供 provider 类型的静态元数据；工厂从 DB 读取管理员
配置的 provider 实例与阶段指派，解析出每个阶段的有序 provider 列表，
供 ScriptWriter 按阶段取用并在失败时逐级降级。

DB 无任何配置时回退到 env ZHIPU_API_KEY 构造的 ZhipuLLMProvider，保留
「无 Key 也能跑 / 自动降级」承诺。
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.providers.llm.base_llm import LLMProviderBase
from app.providers.llm.claude import DEFAULT_MODEL as CLAUDE_DEFAULT_MODEL
from app.providers.llm.claude import ClaudeLLMProvider
from app.providers.llm.deepseek import DEFAULT_MODEL as DEEPSEEK_DEFAULT_MODEL
from app.providers.llm.deepseek import DeepSeekLLMProvider
from app.providers.llm.openai import DEFAULT_MODEL as OPENAI_DEFAULT_MODEL
from app.providers.llm.openai import OpenAILLMProvider
from app.providers.llm.zhipu import DEFAULT_BASE_URL as GLM_DEFAULT_BASE_URL
from app.providers.llm.zhipu import DEFAULT_MODEL as GLM_DEFAULT_MODEL
from app.providers.llm.zhipu import ZhipuLLMProvider
from app.schemas.llm import ProviderMeta, ProviderModelInfo, StageMeta
from app.services.settings_service import get_effective_key

if TYPE_CHECKING:
    from app.models.llm_provider import LLMProviderConfig

logger = logging.getLogger(__name__)


# ── 流水线阶段定义 ────────────────────────────────────

#: 各阶段 key（与 LLMStageAssignment.stage_key 一致）。
LLM_STAGES: list[StageMeta] = [
    StageMeta(
        stage_key="default",
        label="默认 / 兜底",
        description="未单独指派的阶段及失败降级时使用。",
    ),
    StageMeta(
        stage_key="course_metadata",
        label="课程元信息推断",
        description="Stage 0：推断课程标题 / 学科 / 年级 / 受众。",
    ),
    StageMeta(
        stage_key="outline",
        label="教学大纲（Outline Agent）",
        description="Stage 1：全课程叙事弧线与各知识点教学策略。",
    ),
    StageMeta(
        stage_key="scene",
        label="分镜讲稿（Scene Agent）",
        description="Stage 2：逐知识点口语化讲稿 + 画面类型 + SSML 标注。",
    ),
    StageMeta(
        stage_key="review",
        label="全片审校（Review Agent）",
        description="Stage 3：全课程质量审校与衔接修正。",
    ),
]

ALL_STAGE_KEYS: list[str] = [s.stage_key for s in LLM_STAGES]


# ── Provider 类型注册表 ───────────────────────────────


def _models(*ids: str) -> list[ProviderModelInfo]:
    return [ProviderModelInfo(model_id=i, label=i) for i in ids]


PROVIDER_REGISTRY: dict[str, ProviderMeta] = {
    "glm": ProviderMeta(
        provider_type="glm",
        label="智谱 GLM",
        icon_key="glm",
        default_base_url=GLM_DEFAULT_BASE_URL,
        default_model=GLM_DEFAULT_MODEL,
        supports_thinking=True,
        models=_models(
            "glm-4.7-flash",
            "glm-4.7",
            "glm-4-plus",
            "glm-4-air",
        ),
        key_label="智谱 API Key",
        key_url="https://open.bigmodel.cn",
    ),
    "openai": ProviderMeta(
        provider_type="openai",
        label="OpenAI GPT",
        icon_key="openai",
        default_base_url="https://api.openai.com/v1",
        default_model=OPENAI_DEFAULT_MODEL,
        supports_thinking=False,
        models=_models(
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
            "o3-mini",
        ),
        key_label="OpenAI API Key",
        key_url="https://platform.openai.com/api-keys",
    ),
    "deepseek": ProviderMeta(
        provider_type="deepseek",
        label="DeepSeek",
        icon_key="deepseek",
        default_base_url="https://api.deepseek.com",
        default_model=DEEPSEEK_DEFAULT_MODEL,
        supports_thinking=True,
        models=_models(
            "deepseek-v4-flash",
            "deepseek-v4-pro",
        ),
        key_label="DeepSeek API Key",
        key_url="https://platform.deepseek.com/api_keys",
    ),
    "claude": ProviderMeta(
        provider_type="claude",
        label="Anthropic Claude",
        icon_key="claude",
        default_base_url="https://api.anthropic.com",
        default_model=CLAUDE_DEFAULT_MODEL,
        supports_thinking=True,
        models=_models(
            "claude-fable-5",
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5",
        ),
        key_label="Anthropic API Key",
        key_url="https://console.anthropic.com/settings/keys",
    ),
}

#: provider_type → 构造类。
_PROVIDER_CLASS = {
    "glm": ZhipuLLMProvider,
    "openai": OpenAILLMProvider,
    "deepseek": DeepSeekLLMProvider,
    "claude": ClaudeLLMProvider,
}


def build_provider_from_config(config: "LLMProviderConfig") -> LLMProviderBase | None:
    """根据一条 DB 配置构造 provider 实例。未知类型返回 None。"""
    meta = PROVIDER_REGISTRY.get(config.provider_type)
    cls = _PROVIDER_CLASS.get(config.provider_type)
    if meta is None or cls is None:
        logger.warning("未知 provider_type: %s", config.provider_type)
        return None
    model = (config.model_id or meta.default_model).strip() or meta.default_model
    base_url = (
        config.base_url or meta.default_base_url
    ).strip() or meta.default_base_url
    return cls(
        api_key=config.api_key,
        model=model,
        base_url=base_url,
        timeout=settings.LLM_TIMEOUT,
    )


# ── 阶段 → 有序 provider 列表解析 ─────────────────────


async def _load_enabled_configs(db: AsyncSession) -> list["LLMProviderConfig"]:
    """加载所有已启用、未软删的 provider 配置，按 sort_order 升序。"""
    from app.models.llm_provider import LLMProviderConfig

    result = await db.execute(
        select(LLMProviderConfig)
        .where(LLMProviderConfig.is_enabled.is_(True))
        .where(LLMProviderConfig.deleted_at.is_(None))
        .order_by(LLMProviderConfig.sort_order.asc())
    )
    return list(result.scalars().all())


async def _load_assignments(db: AsyncSession) -> dict[str, str | None]:
    """加载阶段指派：stage_key → config_id（字符串）或 None。"""
    from app.models.llm_provider import LLMStageAssignment

    result = await db.execute(select(LLMStageAssignment))
    mapping: dict[str, str | None] = {stage: None for stage in ALL_STAGE_KEYS}
    for row in result.scalars().all():
        mapping[row.stage_key] = str(row.config_id) if row.config_id else None
    return mapping


def _fallback_env_provider() -> LLMProviderBase | None:
    """DB 无配置时回退到 env ZHIPU_API_KEY 构造的 GLM provider。"""
    api_key = get_effective_key("ZHIPU_API_KEY")
    if not api_key:
        return None
    return ZhipuLLMProvider(
        api_key=api_key,
        model=settings.ZHIPU_MODEL,
        base_url=settings.ZHIPU_BASE_URL,
        timeout=settings.LLM_TIMEOUT,
    )


async def resync_zhipu_mirror(db: AsyncSession) -> None:
    """把首个已启用 GLM 配置的 API Key 镜像到运行时 ZHIPU_API_KEY。

    使「LLM 管理」成为智谱 Key 的唯一配置入口：CogVideoX 视频生成与
    成本护栏仍读运行时 ``ZHIPU_API_KEY``（旧同步路径），此处把 LLM 管理
    页保存的 GLM Key 同步过去，二者无需各自重复配置。无已启用 GLM 配置
    时清除镜像（回退 .env 的 ZHIPU_API_KEY）。
    """
    from app.models.llm_provider import LLMProviderConfig
    from app.services.settings_service import set_runtime_setting

    result = await db.execute(
        select(LLMProviderConfig)
        .where(LLMProviderConfig.provider_type == "glm")
        .where(LLMProviderConfig.is_enabled.is_(True))
        .where(LLMProviderConfig.deleted_at.is_(None))
        .order_by(LLMProviderConfig.sort_order.asc())
        .limit(1)
    )
    cfg = result.scalars().one_or_none()
    set_runtime_setting("ZHIPU_API_KEY", cfg.api_key if cfg else None)


async def get_llm_providers_for_stages(
    db: AsyncSession | None = None,
) -> dict[str, list[LLMProviderBase]]:
    """解析每个阶段的有序 provider 列表。

    每个阶段的列表构造：
      1. 该阶段指派的 config（若已启用）；
      2. default 阶段指派的 config（若已启用且未重复）；
      3. 其余已启用 config，按 sort_order 排序（去重）。

    DB 无任何已启用 config 时，所有阶段回退到 env ZHIPU provider
    （可能为 None，由调用方降级为本地规整）。

    Args:
        db: 可选 DB 会话；不传则内部自建 session（后台任务场景）。
    """
    owns_session = db is None
    if owns_session:
        async with async_session_factory() as db:  # type: ignore[arg-type]
            return await get_llm_providers_for_stages(db)  # type: ignore[arg-type]

    configs = await _load_enabled_configs(db)  # type: ignore[arg-type]
    if not configs:
        env_provider = _fallback_env_provider()
        unit = [env_provider] if env_provider else []
        return {stage: list(unit) for stage in ALL_STAGE_KEYS}

    config_by_id: dict[str, LLMProviderConfig] = {str(c.id): c for c in configs}
    assignments = await _load_assignments(db)  # type: ignore[arg-type]

    default_id = assignments.get("default")

    def _build_for_stage(stage: str) -> list[LLMProviderBase]:
        ordered: list[LLMProviderBase] = []
        seen_ids: set[str] = set()

        def _try_config(cid: str | None) -> None:
            if not cid:
                return
            if cid in seen_ids:
                return
            cfg = config_by_id.get(cid)
            if cfg is None:
                return
            provider = build_provider_from_config(cfg)
            if provider is not None:
                ordered.append(provider)
                seen_ids.add(cid)

        # 1) 阶段指派优先
        _try_config(assignments.get(stage))
        # 2) 默认指派
        if stage != "default":
            _try_config(default_id)
        # 3) 其余已启用 config 按 sort_order 兜底
        for cfg in configs:
            _try_config(str(cfg.id))

        return ordered

    return {stage: _build_for_stage(stage) for stage in ALL_STAGE_KEYS}


def make_resolver(
    stage_map: dict[str, list[LLMProviderBase]],
) -> Callable[[str], list[LLMProviderBase]]:
    """把阶段→列表映射封装为 ScriptWriter 用的同步 resolver。

    resolver(stage_key) 返回该阶段的 provider 列表；空则回退到 default。
    """

    def _resolver(stage_key: str) -> list[LLMProviderBase]:
        return stage_map.get(stage_key) or stage_map.get("default") or []

    return _resolver


# ── 遗留兼容入口 ──────────────────────────────────────


def get_llm_provider() -> ZhipuLLMProvider | None:
    """遗留兼容：构造默认 LLM Provider（env ZHIPU_API_KEY）。

    新代码应使用 get_llm_providers_for_stages()。本函数保留供 health_service
    等只需判断「是否有可用 LLM」的场景。
    """
    return _fallback_env_provider()  # type: ignore[return-value]


__all__ = [
    "ALL_STAGE_KEYS",
    "LLM_STAGES",
    "PROVIDER_REGISTRY",
    "build_provider_from_config",
    "get_llm_provider",
    "get_llm_providers_for_stages",
    "make_resolver",
    "resync_zhipu_mirror",
    "ClaudeLLMProvider",
    "DeepSeekLLMProvider",
    "OpenAILLMProvider",
    "ZhipuLLMProvider",
]
