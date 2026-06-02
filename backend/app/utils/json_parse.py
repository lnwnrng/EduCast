"""健壮的 LLM JSON 输出解析工具。

LLM 返回的内容可能带有 ```json 围栏、前置的推理/解释文字，或在 JSON
前后混入说明。`extract_json` 尽力从中提取第一个完整的 JSON 对象。
"""

import json
import re
from typing import Any

# 匹配 ```json ... ``` 或 ``` ... ``` 代码围栏
_FENCE_RE = re.compile(
    r"```(?:json)?\s*(?P<body>.*?)```",
    re.IGNORECASE | re.DOTALL,
)


def extract_json(text: str | None) -> dict[str, Any] | None:
    """从 LLM 文本输出中提取首个 JSON 对象。

    处理顺序:
      1. 整段直接尝试 json.loads。
      2. 提取 ```json``` 代码围栏内的内容再尝试。
      3. 用括号配平定位首个完整 ``{...}`` 子串再尝试。

    Args:
        text: LLM 返回的原始文本。

    Returns:
        解析得到的 dict；无法解析时返回 None。
    """
    if not text:
        return None

    stripped = text.strip()

    # 1. 直接解析
    obj = _try_loads(stripped)
    if obj is not None:
        return obj

    # 2. 代码围栏
    for match in _FENCE_RE.finditer(stripped):
        obj = _try_loads(match.group("body").strip())
        if obj is not None:
            return obj

    # 3. 括号配平扫描
    candidate = _find_balanced_object(stripped)
    if candidate is not None:
        obj = _try_loads(candidate)
        if obj is not None:
            return obj

    return None


def _try_loads(s: str) -> dict[str, Any] | None:
    """尝试把字符串解析为 JSON dict，失败返回 None。"""
    if not s:
        return None
    try:
        result = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return None
    return result if isinstance(result, dict) else None


def _find_balanced_object(s: str) -> str | None:
    """定位首个括号配平的 ``{...}`` 子串（跳过字符串内的花括号）。"""
    start = s.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(s)):
        ch = s[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]

    return None
