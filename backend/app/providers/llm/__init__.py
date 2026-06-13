"""LLM Provider 子包。"""

from app.config import settings
from app.providers.llm.zhipu import ZhipuLLMProvider
from app.services.settings_service import get_effective_key


def get_llm_provider() -> ZhipuLLMProvider | None:
    """构造默认 LLM Provider。

    读取全局配置；未配置 ZHIPU_API_KEY 时返回 None（供上层降级处理，
    并使无 Key 的测试/开发环境不发起真实调用）。
    支持运行时通过前端设置页面配置 API Key。
    """
    api_key = get_effective_key("ZHIPU_API_KEY")
    if not api_key:
        return None
    return ZhipuLLMProvider(
        api_key=api_key,
        model=settings.ZHIPU_MODEL,
        base_url=settings.ZHIPU_BASE_URL,
        timeout=settings.LLM_TIMEOUT,
    )


__all__ = ["ZhipuLLMProvider", "get_llm_provider"]
