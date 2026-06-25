"""智谱 GLM-4.7-Flash LLM Provider。

GLM-4.7-Flash（2026-01 起免费，替代 GLM-4.5-Flash）是混合思考模型，通过
OpenAI 兼容端点调用：

    POST {base_url}/chat/completions
    Authorization: Bearer <api_key>

用于脚本编排、分镜规划、出题、合规审核。免费档，成本为 0。
"""

from app.providers.llm.openai_compat import OpenAICompatibleLLMProvider

DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-4.7-flash"


class ZhipuLLMProvider(OpenAICompatibleLLMProvider):
    """智谱 GLM Provider（OpenAI 兼容端点，支持 thinking 字段）。

    保留原类名以兼容既有引用与测试。核心实现见 OpenAICompatibleLLMProvider。
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
            provider_type="glm",
            provider_name="zhipu_glm4.7_flash",
            supports_thinking=True,
            timeout=timeout,
        )
