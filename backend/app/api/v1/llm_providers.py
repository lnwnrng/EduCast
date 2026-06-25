"""LLM 模型管理 API — 多模型路由配置（cc-switch 风格）。

管理员在此配置 Claude / OpenAI / GLM / DeepSeek 的 API Key、base_url、
型号，并为流水线各阶段指派 provider。全部端点要求管理员权限。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import require_admin
from app.models.llm_provider import LLMProviderConfig, LLMStageAssignment
from app.models.user import User
from app.providers.llm import (
    ALL_STAGE_KEYS,
    LLM_STAGES,
    PROVIDER_REGISTRY,
    build_provider_from_config,
    resync_zhipu_mirror,
)
from app.schemas.llm import (
    LLMProviderConfigCreate,
    LLMProviderConfigResponse,
    LLMProviderConfigUpdate,
    LLMStageAssignmentBulkUpdate,
    LLMStageAssignmentResponse,
    LLMTestResult,
)

router = APIRouter(prefix="/llm-providers", tags=["LLM 模型管理"])


def _mask_api_key(value: str) -> str:
    """脱敏 API Key。"""
    if not value:
        return ""
    if len(value) > 10:
        return value[:6] + "****" + value[-4:]
    return "****"


def _to_config_response(cfg: LLMProviderConfig) -> LLMProviderConfigResponse:
    """把 ORM 行转为响应（api_key 脱敏）。"""
    return LLMProviderConfigResponse(
        id=cfg.id,
        provider_type=cfg.provider_type,
        name=cfg.name,
        base_url=cfg.base_url,
        model_id=cfg.model_id,
        is_enabled=cfg.is_enabled,
        sort_order=cfg.sort_order,
        thinking_disabled=cfg.thinking_disabled,
        api_key_masked=_mask_api_key(cfg.api_key),
        is_configured=bool(cfg.api_key),
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


# ── 注册表元数据 ───────────────────────────────────────


@router.get("/registry")
async def get_registry(
    _current_user: User = Depends(require_admin),
) -> dict:
    """返回 provider 类型与阶段的静态元数据（供前端渲染）。"""
    return {
        "providers": [p.model_dump() for p in PROVIDER_REGISTRY.values()],
        "stages": [s.model_dump() for s in LLM_STAGES],
    }


# ── Provider 配置 CRUD ────────────────────────────────


@router.get("/configs", response_model=list[LLMProviderConfigResponse])
async def list_configs(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> list[LLMProviderConfigResponse]:
    """列出所有 provider 配置（含已禁用，按 sort_order 升序）。"""
    result = await db.execute(
        select(LLMProviderConfig)
        .where(LLMProviderConfig.deleted_at.is_(None))
        .order_by(LLMProviderConfig.sort_order.asc())
    )
    return [_to_config_response(c) for c in result.scalars().all()]


@router.post("/configs", response_model=LLMProviderConfigResponse, status_code=201)
async def create_config(
    data: LLMProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> LLMProviderConfigResponse:
    """新建 provider 配置。"""
    if data.provider_type not in PROVIDER_REGISTRY:
        raise HTTPException(400, f"不支持的 provider 类型: {data.provider_type}")
    meta = PROVIDER_REGISTRY[data.provider_type]
    cfg = LLMProviderConfig(
        provider_type=data.provider_type,
        name=data.name,
        api_key=data.api_key.strip(),
        base_url=(data.base_url or meta.default_base_url).strip(),
        model_id=(data.model_id or meta.default_model).strip(),
        is_enabled=data.is_enabled,
        sort_order=data.sort_order,
        thinking_disabled=data.thinking_disabled,
    )
    db.add(cfg)
    await db.flush()
    await db.refresh(cfg)
    await resync_zhipu_mirror(db)
    return _to_config_response(cfg)


@router.put("/configs/{config_id}", response_model=LLMProviderConfigResponse)
async def update_config(
    config_id: str,
    data: LLMProviderConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> LLMProviderConfigResponse:
    """更新 provider 配置（api_key 留空表示不变）。"""
    cfg = await _get_config_or_404(db, config_id)
    if data.name is not None:
        cfg.name = data.name
    if data.api_key is not None and data.api_key.strip():
        cfg.api_key = data.api_key.strip()
    if data.base_url is not None:
        cfg.base_url = data.base_url
    if data.model_id is not None:
        cfg.model_id = data.model_id
    if data.is_enabled is not None:
        cfg.is_enabled = data.is_enabled
    if data.sort_order is not None:
        cfg.sort_order = data.sort_order
    if data.thinking_disabled is not None:
        cfg.thinking_disabled = data.thinking_disabled
    await db.flush()
    await db.refresh(cfg)
    await resync_zhipu_mirror(db)
    return _to_config_response(cfg)


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> dict:
    """删除 provider 配置，并清空引用它的阶段指派。"""
    cfg = await _get_config_or_404(db, config_id)
    cfg_uuid = cfg.id

    # 清空引用该 config 的阶段指派
    result = await db.execute(
        select(LLMStageAssignment).where(LLMStageAssignment.config_id == cfg_uuid)
    )
    for assign in result.scalars().all():
        assign.config_id = None

    await db.delete(cfg)
    await resync_zhipu_mirror(db)
    return {"message": "配置已删除"}


@router.post("/configs/{config_id}/test", response_model=LLMTestResult)
async def test_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> LLMTestResult:
    """对单个 provider 配置发起最小化连通性探测。"""
    import httpx

    cfg = await _get_config_or_404(db, config_id)
    if not cfg.api_key:
        return LLMTestResult(ok=False, message="API Key 为空，请先填写")
    provider = build_provider_from_config(cfg)
    if provider is None:
        return LLMTestResult(ok=False, message="无法构造 provider（未知类型）")

    try:
        result = await provider.chat(
            [{"role": "user", "content": "hi"}],
            temperature=0.3,
            max_tokens=10,
            thinking_disabled=cfg.thinking_disabled,
        )
        if result.content is not None:
            return LLMTestResult(
                ok=True,
                message=f"{provider.provider_name} 连通正常，模型 {cfg.model_id}",
            )
        return LLMTestResult(ok=False, message="API 返回空内容")
    except httpx.TimeoutException:
        return LLMTestResult(
            ok=False,
            message="检测超时：无法连接 API 服务器，请检查网络/代理/VPN。",
        )
    except httpx.ConnectError:
        return LLMTestResult(ok=False, message="网络连接失败：无法访问 API 服务器。")
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        return LLMTestResult(ok=False, message=f"验证失败: {msg[:200]}")


async def _get_config_or_404(db: AsyncSession, config_id: str) -> LLMProviderConfig:
    """按 id 取配置，不存在则 404。"""
    try:
        cfg_uuid = uuid.UUID(config_id)
    except ValueError as exc:
        raise HTTPException(400, "无效的配置 ID") from exc
    result = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.id == cfg_uuid)
    )
    cfg = result.scalar_one_or_none()
    if cfg is None or cfg.deleted_at is not None:
        raise HTTPException(404, "配置不存在")
    return cfg


# ── 阶段指派 ─────────────────────────────────────────


@router.get("/stages", response_model=list[LLMStageAssignmentResponse])
async def list_stages(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> list[LLMStageAssignmentResponse]:
    """列出 5 个阶段的当前指派（含被指派 config 的脱敏信息）。"""
    # 取所有阶段指派
    result = await db.execute(select(LLMStageAssignment))
    assign_map: dict[str, LLMStageAssignment] = {
        a.stage_key: a for a in result.scalars().all()
    }

    # 取被引用的 config
    referenced_ids = {
        a.config_id for a in assign_map.values() if a.config_id is not None
    }
    config_map: dict[uuid.UUID, LLMProviderConfig] = {}
    if referenced_ids:
        res = await db.execute(
            select(LLMProviderConfig).where(LLMProviderConfig.id.in_(referenced_ids))
        )
        config_map = {c.id: c for c in res.scalars().all()}

    responses: list[LLMStageAssignmentResponse] = []
    for stage_key in ALL_STAGE_KEYS:
        assign = assign_map.get(stage_key)
        cfg = None
        if assign and assign.config_id:
            raw = config_map.get(assign.config_id)
            if raw is not None and raw.deleted_at is None and raw.is_enabled:
                cfg = _to_config_response(raw)
            elif raw is not None and raw.deleted_at is None and not raw.is_enabled:
                # 指向已禁用配置 — 仍返回以便前端提示，但标记
                cfg = _to_config_response(raw)
        responses.append(
            LLMStageAssignmentResponse(
                stage_key=stage_key,
                config_id=assign.config_id if assign else None,
                config=cfg,
            )
        )
    return responses


@router.put("/stages", response_model=list[LLMStageAssignmentResponse])
async def update_stages(
    data: LLMStageAssignmentBulkUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> list[LLMStageAssignmentResponse]:
    """批量更新阶段指派。未提供的 stage 不变；config_id 为 null 表示跟随默认。"""
    valid_stages = set(ALL_STAGE_KEYS)
    for item in data.assignments:
        if item.stage_key not in valid_stages:
            raise HTTPException(400, f"未知阶段: {item.stage_key}")

    result = await db.execute(select(LLMStageAssignment))
    assign_map: dict[str, LLMStageAssignment] = {
        a.stage_key: a for a in result.scalars().all()
    }

    # 校验 config_id 存在且未删除
    requested_ids = {
        item.config_id for item in data.assignments if item.config_id is not None
    }
    valid_ids: set[uuid.UUID] = set()
    if requested_ids:
        res = await db.execute(
            select(LLMProviderConfig).where(LLMProviderConfig.id.in_(requested_ids))
        )
        valid_ids = {c.id for c in res.scalars().all() if c.deleted_at is None}

    for item in data.assignments:
        assign = assign_map.get(item.stage_key)
        if assign is None:
            assign = LLMStageAssignment(stage_key=item.stage_key, config_id=None)
            db.add(assign)
            assign_map[item.stage_key] = assign
        if item.config_id is not None and item.config_id not in valid_ids:
            raise HTTPException(400, "指派的配置不存在或已删除")
        assign.config_id = item.config_id

    await db.flush()
    # 复用 list_stages 逻辑返回最新状态
    return await list_stages(db, _current_user=_current_user)  # type: ignore[arg-type]
