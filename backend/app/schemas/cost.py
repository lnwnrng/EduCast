"""成本与监控 Schema。"""

from pydantic import BaseModel, Field


class CostEstimate(BaseModel):
    """IR 生成成本预估。

    - ``total``：潜在成本——把数字人/生成式分镜按付费 API 费率全算（用于展示）。
    - ``chargeable``：本次实际会计费的成本——仅统计已激活（配置了 API Key）的付费
      能力；未接付费 API 时这些分镜降级为免费课件页，计 0。配额护栏按此值拦截。
    """

    total: float = Field(default=0.0, description="潜在预估总成本（含未接的付费能力）")
    chargeable: float = Field(
        default=0.0, description="本次实际计费成本（仅已激活能力）"
    )
    breakdown: dict[str, float] = Field(
        default_factory=dict, description="按画面类型分类的潜在成本明细"
    )
    currency: str = Field(default="CNY", description="币种")


class CostSummary(BaseModel):
    """项目成本与存储汇总。"""

    project_id: str
    task_count: int
    status_counts: dict[str, int]
    estimated_total: float
    actual_total: float
    storage_bytes: int


class DashboardStats(BaseModel):
    """全局监控面板统计。"""

    task_count: int
    status_counts: dict[str, int]
    estimated_total: float
    actual_total: float
    storage_bytes: int
    recent_tasks: list[dict] = Field(default_factory=list)
