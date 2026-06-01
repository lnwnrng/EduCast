"""输入指纹 Hash 工具 — 用于幂等性保证与缓存复用。"""

import hashlib
import json
from typing import Union


def compute_input_hash(data: Union[dict, str, bytes]) -> str:
    """计算输入数据的 SHA256 摘要。

    用于:
    - 子任务幂等键: 相同输入不重复生成
    - Provider 缓存: 相同请求命中缓存
    """
    if isinstance(data, dict):
        serialized = json.dumps(data, sort_keys=True).encode()
    elif isinstance(data, str):
        serialized = data.encode()
    else:
        serialized = data

    return hashlib.sha256(serialized).hexdigest()
