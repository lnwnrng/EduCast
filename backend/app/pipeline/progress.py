"""进度映射单一来源 —— 全程单调递增的阶段区间与默认子步骤文案。

各 Service（parser / scriptwriter / composition）不再散落魔法数字，
统一通过 ``band_progress(phase, done, total)`` 把「阶段内完成度」映射到
全局百分比，保证进度条单调递增、跨阶段不倒退。

关键不倒退保证：
  - ``reviewing`` 区间为 (45, 45)，是个检查点；教师放行后
    ``generating`` 从 45 起算，绝不回退到更小的值。
"""

# 全程单调递增的阶段区间 [lo, hi]
PHASE_BANDS: dict[str, tuple[int, int]] = {
    "pending": (0, 0),
    "parsing": (0, 15),
    "scripting": (15, 45),  # 按知识点细分
    "reviewing": (45, 45),  # 检查点：不卡死、不倒退
    "generating": (45, 85),  # 按分镜细分
    "composing": (85, 98),
    "completed": (100, 100),
    "failed": (0, 0),  # 实际不用于换算（失败保留现值）
}


def band_progress(phase: str, done: int, total: int) -> int:
    """把阶段内完成度 (done/total) 映射到该阶段的全局百分比区间。

    Args:
        phase: 阶段名（须在 ``PHASE_BANDS`` 内）。
        done: 已完成数量。
        total: 总数量；<=0 时返回区间下界。

    Returns:
        全局进度百分比（int）。
    """
    lo, hi = PHASE_BANDS.get(phase, (0, 0))
    if total <= 0:
        return lo
    return lo + int((hi - lo) * min(done, total) / total)


# status → 默认子步骤文案（前端无 step_detail 时兜底，旧任务/轮询也能拿到）
DEFAULT_STEP_DETAIL: dict[str, str] = {
    "pending": "排队中…",
    "parsing": "解析课件中…",
    "scripting": "编排讲稿中…",
    "reviewing": "等待教师审核",
    "generating": "生成分镜素材中…",
    "composing": "合成视频中…",
    "completed": "已完成",
    "failed": "处理失败",
}
