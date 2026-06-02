"""成本与监控 Schema。"""

from pydantic import BaseModel, Field


class CostEstimate(BaseModel):
    """IR 生成成本预估。"""

    total: float = Field(default=0.0, description="预估总成本")
    breakdown: dict[str, float] = Field(
        default_factory=dict, description="按画面类型分类的成本明细"
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
