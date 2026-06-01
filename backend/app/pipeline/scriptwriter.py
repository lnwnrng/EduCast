"""LLM 脚本编排器 — 将 IR 草稿扩写为可生产 IR。

使用 LLM 完成:
- 讲稿生成与口语化
- 分镜规划与画面类型指定
- 画面提示词生成
- 字幕与旁白对齐
- 知识点标注
- 出题（供评估模块）
"""

import logging

from app.ir.schema import CourseIR
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ScriptWriter:
    """LLM 脚本编排器。"""

    def __init__(self, llm_provider: BaseProvider) -> None:
        self._llm = llm_provider

    async def enhance_ir(self, draft_ir: CourseIR) -> CourseIR:
        """将 IR 草稿扩写为完整可生产 IR。

        TODO(P1): 实现 LLM 调用:
        1. 构造系统提示词（学科、风格、受众）
        2. 按知识点逐个调用 LLM 生成讲稿
        3. 规划分镜（scene_type 分配）
        4. 生成字幕文本
        5. 生成练习题种子

        当前为占位实现，直接返回输入 IR。
        """
        logger.info(
            "脚本编排 (占位实现): %s — %d 章节",
            draft_ir.title,
            len(draft_ir.chapters),
        )
        # TODO: 调用 self._llm.submit() 完成编排
        return draft_ir
