"""运行时设置 API — 前端配置 API Key 等参数。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.middleware.auth import get_current_user_from_cookie
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.services.settings_service import (
    API_KEY_DEFINITIONS,
    load_runtime_settings,
    save_runtime_settings,
    verify_api_key,
)

router = APIRouter(prefix="/settings", tags=["系统设置"])


class UpdateSettingsRequest(BaseModel):
    """更新运行时设置。"""
    settings: dict[str, str]


@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_user_from_cookie),
):
    """获取 API Key 配置定义和当前状态（仅管理员）。"""
    if current_user.role != "admin":
        return {"items": [], "message": "仅管理员可查看"}

    runtime = load_runtime_settings()
    items = []
    for defn in API_KEY_DEFINITIONS:
        key = defn["key"]
        is_secret = defn.get("is_secret", True)
        # 检查是否已配置（运行时 or 环境变量）
        runtime_val = runtime.get(key, "").strip()
        is_configured = bool(runtime_val)
        # 脱敏显示：密钥类截断，普通配置类显示完整
        masked = ""
        if runtime_val:
            if is_secret:
                masked = runtime_val[:6] + "****" + runtime_val[-4:] if len(runtime_val) > 10 else "****"
            else:
                masked = runtime_val

        items.append({
            **defn,
            "is_configured": is_configured,
            "masked_value": masked,
        })

    return {"items": items}


@router.get("/api-keys/values")
async def get_api_key_values(
    current_user: User = Depends(get_current_user_from_cookie),
):
    """获取当前 API Key 值（仅管理员，用于编辑表单回填）。"""
    if current_user.role != "admin":
        return {"settings": {}}

    runtime = load_runtime_settings()
    result = {}
    for defn in API_KEY_DEFINITIONS:
        key = defn["key"]
        result[key] = runtime.get(key, "")

    return {"settings": result}


@router.put("/api-keys", response_model=SuccessResponse)
async def update_api_keys(
    data: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """更新 API Key 配置（仅管理员）。"""
    if current_user.role != "admin":
        return SuccessResponse(message="仅管理员可修改")

    # 只允许修改已定义的 key
    allowed_keys = {d["key"] for d in API_KEY_DEFINITIONS}
    runtime = load_runtime_settings()

    for key, value in data.settings.items():
        if key in allowed_keys:
            runtime[key] = value.strip()

    save_runtime_settings(runtime)

    configured = [k for k, v in runtime.items() if v and k in allowed_keys]
    return SuccessResponse(message=f"设置已保存，已配置: {', '.join(configured) or '无'}")


class TestApiKeyRequest(BaseModel):
    """测试 API Key 连通性。"""
    key: str
    value: str


@router.post("/api-keys/test")
async def test_api_key(
    data: TestApiKeyRequest,
    current_user: User = Depends(get_current_user_from_cookie),
):
    """验证指定 API Key 是否有效（仅管理员）。"""
    if current_user.role != "admin":
        return {"ok": False, "message": "仅管理员可检测"}

    allowed_keys = {d["key"] for d in API_KEY_DEFINITIONS}
    if data.key not in allowed_keys:
        return {"ok": False, "message": f"不支持的配置项: {data.key}"}

    result = await verify_api_key(data.key, data.value)
    return result
