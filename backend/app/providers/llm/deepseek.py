"""DeepSeek 聊天补全（OpenAI 兼容）。

端点: POST https://api.deepseek.com/chat/completions, Bearer 鉴权。
当前型号 deepseek-v4-flash / deepseek-v4-pro（deepseek-chat / deepseek-reasoner
已于 2026/07/24 弃用）。deepseek-v4-flash 为混合思考模型，关闭推理以稳定
结构化输出。
"""

from app.providers.llm.openai_compat import OpenAICompatibleLLMProvider

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


class DeepSeekLLMProvider(OpenAICompatibleLLMProvider):
    """DeepSeek Provider（OpenAI 兼容端点，支持 thinking 字段）。"""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            api_key,
            model,
            base_url,
            provider_type="deepseek",
            provider_name="deepseek",
            supports_thinking=True,
            timeout=timeout,
        )
