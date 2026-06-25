"""OpenAI GPT 系列聊天补全。"""

from app.providers.llm.openai_compat import OpenAICompatibleLLMProvider

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4.1-mini"


class OpenAILLMProvider(OpenAICompatibleLLMProvider):
    """OpenAI GPT 系列 Provider（OpenAI 兼容端点）。

    新型号统一使用 max_completion_tokens；不支持 thinking 字段。
    """

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
            provider_type="openai",
            provider_name="openai",
            supports_thinking=False,
            timeout=timeout,
        )
