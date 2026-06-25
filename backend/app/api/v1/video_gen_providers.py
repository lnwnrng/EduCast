"""视频生成模型管理 API — 多模型配置（cc-switch 风格）。

管理员在此配置 CogVideoX / Kling / MiniMax 的 API Key、base_url、型号，并
激活一条供合成层使用。全部端点要求管理员权限。激活/保存时镜像到运行时
VIDEO_GEN_*，供同步路径 `get_video_gen_provider()` 取用。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import require_admin
from app.models.user import User
from app.models.video_gen_provider import VideoGenProviderConfig
from app.providers.video_gen import (
    VIDEO_GEN_REGISTRY,
    build_video_gen_provider_from_config,
    resync_video_gen_mirror,
)
from app.schemas.video_gen import (
    VideoGenProviderConfigCreate,
    VideoGenProviderConfigResponse,
    VideoGenProviderConfigUpdate,
    VideoGenTestResult,
)

router = APIRouter(prefix="/video-gen-providers", tags=["视频生成模型管理"])


def _mask_api_key(value: str) -> str:
    if not value:
        return ""
    if len(value) > 10:
        return value[:6] + "****" + value[-4:]
    return "****"


def _to_response(cfg: VideoGenProviderConfig) -> VideoGenProviderConfigResponse:
    return VideoGenProviderConfigResponse(
        id=cfg.id,
        provider_type=cfg.provider_type,
        name=cfg.name,
        base_url=cfg.base_url,
        model_id=cfg.model_id,
        is_enabled=cfg.is_enabled,
        is_active=cfg.is_active,
        sort_order=cfg.sort_order,
        api_key_masked=_mask_api_key(cfg.api_key),
        is_configured=bool(cfg.api_key),
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


async def _get_or_404(db: AsyncSession, config_id: str) -> VideoGenProviderConfig:
    try:
        cfg_uuid = uuid.UUID(config_id)
    except ValueError as exc:
        raise HTTPException(400, "无效的配置 ID") from exc
    result = await db.execute(
        select(VideoGenProviderConfig).where(VideoGenProviderConfig.id == cfg_uuid)
    )
    cfg = result.scalar_one_or_none()
    if cfg is None or cfg.deleted_at is not None:
        raise HTTPException(404, "配置不存在")
    return cfg


async def _deactivate_others(db: AsyncSession, exclude_id: uuid.UUID) -> None:
    """把除 exclude_id 外的所有配置置为非激活。"""
    result = await db.execute(
        select(VideoGenProviderConfig).where(
            VideoGenProviderConfig.is_active.is_(True),
            VideoGenProviderConfig.id != exclude_id,
        )
    )
    for other in result.scalars().all():
        other.is_active = False


@router.get("/registry")
async def get_registry(
    _current_user: User = Depends(require_admin),
) -> dict:
    """返回视频生成 provider 类型的静态元数据（供前端渲染）。"""
    return {"providers": [p.model_dump() for p in VIDEO_GEN_REGISTRY.values()]}


@router.get("/configs", response_model=list[VideoGenProviderConfigResponse])
async def list_configs(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> list[VideoGenProviderConfigResponse]:
    result = await db.execute(
        select(VideoGenProviderConfig)
        .where(VideoGenProviderConfig.deleted_at.is_(None))
        .order_by(VideoGenProviderConfig.sort_order.asc())
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.post("/configs", response_model=VideoGenProviderConfigResponse, status_code=201)
async def create_config(
    data: VideoGenProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> VideoGenProviderConfigResponse:
    if data.provider_type not in VIDEO_GEN_REGISTRY:
        raise HTTPException(400, f"不支持的 provider 类型: {data.provider_type}")
    meta = VIDEO_GEN_REGISTRY[data.provider_type]
    cfg = VideoGenProviderConfig(
        provider_type=data.provider_type,
        name=data.name,
        api_key=data.api_key.strip(),
        base_url=(data.base_url or meta.default_base_url).strip(),
        model_id=(data.model_id or meta.default_model).strip(),
        is_enabled=data.is_enabled,
        is_active=False,  # 新建默认不激活；激活走单独端点
        sort_order=data.sort_order,
    )
    db.add(cfg)
    await db.flush()
    await db.refresh(cfg)
    # 若创建时要求激活
    if data.is_active:
        await _deactivate_others(db, cfg.id)
        cfg.is_active = True
        await db.flush()
    await resync_video_gen_mirror(db)
    return _to_response(cfg)


@router.put("/configs/{config_id}", response_model=VideoGenProviderConfigResponse)
async def update_config(
    config_id: str,
    data: VideoGenProviderConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> VideoGenProviderConfigResponse:
    cfg = await _get_or_404(db, config_id)
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
    await db.flush()
    await db.refresh(cfg)
    await resync_video_gen_mirror(db)
    return _to_response(cfg)


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> dict:
    cfg = await _get_or_404(db, config_id)
    was_active = cfg.is_active
    await db.delete(cfg)
    if was_active:
        await resync_video_gen_mirror(db)
    return {"message": "配置已删除"}


@router.post("/configs/{config_id}/activate")
async def activate_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> dict:
    """激活一条视频生成配置（同时停用其它）。"""
    cfg = await _get_or_404(db, config_id)
    if not cfg.is_enabled:
        raise HTTPException(400, "该配置已禁用，无法激活")
    await _deactivate_others(db, cfg.id)
    cfg.is_active = True
    await db.flush()
    await resync_video_gen_mirror(db)
    return {"message": f"已激活：{cfg.name}"}


@router.post("/configs/{config_id}/test", response_model=VideoGenTestResult)
async def test_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> VideoGenTestResult:
    """对单个视频生成 provider 配置做最小化连通性探测（仅提交+立即查询一次）。"""
    import httpx

    cfg = await _get_or_404(db, config_id)
    if not cfg.api_key:
        return VideoGenTestResult(ok=False, message="API Key 为空，请先填写")
    provider = build_video_gen_provider_from_config(cfg)
    if provider is None:
        return VideoGenTestResult(ok=False, message="无法构造 provider（未知类型）")

    try:
        # 提交一个最小任务：用一句极简 prompt，若返回 task_id 视为连通通过。
        task_id = await provider.submit(
            {"prompt": "a static test image", "image_url": None}
        )
        if task_id:
            return VideoGenTestResult(
                ok=True,
                message=(
                    f"{provider.provider_name} 连通正常，"
                    f"任务已提交（{cfg.model_id}）"
                ),
            )
        return VideoGenTestResult(ok=False, message="未返回 task_id")
    except httpx.TimeoutException:
        return VideoGenTestResult(
            ok=False, message="检测超时：无法连接 API 服务器，请检查网络/代理。"
        )
    except httpx.ConnectError:
        return VideoGenTestResult(
            ok=False, message="网络连接失败：无法访问 API 服务器。"
        )
    except Exception as e:  # noqa: BLE001 — 提交失败可能是参数/权限问题
        msg = str(e)
        # 401/403/4xx 通常是认证或参数问题，但仍代表「可达」
        if "401" in msg or "403" in msg:
            return VideoGenTestResult(ok=False, message=f"认证/权限失败：{msg[:160]}")
        return VideoGenTestResult(ok=False, message=f"验证失败: {msg[:160]}")
