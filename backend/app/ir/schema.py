"""课程脚本 IR 数据结构 — 四层分层结构化脚本。

IR 是课影系统的核心数据结构：
- 解析只产出 IR
- 生成只消费 IR
- 厂商无关、人可校对、机器可消费
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

# ── 枚举 ─────────────────────────────────────────────────


class SceneType(str, Enum):
    """分镜画面类型。"""

    SLIDE = "slide"
    FORMULA_ANIMATION = "formula_animation"
    DIGITAL_HUMAN = "digital_human"
    GENERATIVE_CLIP = "generative_clip"


class DurationStrategy(str, Enum):
    """时长策略。"""

    NARRATION_DRIVEN = "narration_driven"
    FIXED = "fixed"
    AUTO = "auto"


class TransitionType(str, Enum):
    """转场类型。"""

    FADE = "fade"
    CUT = "cut"
    DISSOLVE = "dissolve"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"


class PipPosition(str, Enum):
    """画中画位置。"""

    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_LEFT = "bottom_left"
    TOP_RIGHT = "top_right"
    TOP_LEFT = "top_left"
    FULL_SCREEN = "full_screen"


class PipSize(str, Enum):
    """画中画尺寸。"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ProductionStatus(str, Enum):
    """生产状态。"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── 嵌套模型 ─────────────────────────────────────────────


class VisualSpec(BaseModel):
    """画面规格。"""

    slide_ref: str | None = Field(default=None, description="课件页引用（图片路径）")
    latex_steps: list[str] = Field(
        default_factory=list, description="LaTeX 公式推导步骤"
    )
    image_refs: list[str] = Field(default_factory=list, description="关联图片引用")
    gen_prompt: str | None = Field(default=None, description="生成式片段提示词")
    pip_position: PipPosition = Field(
        default=PipPosition.BOTTOM_RIGHT, description="画中画位置"
    )
    pip_size: PipSize = Field(default=PipSize.SMALL, description="画中画尺寸")


class ProductionMeta(BaseModel):
    """生产元数据 — 记录 Provider 信息与成本。"""

    provider: str | None = Field(default=None, description="所用 Provider 名称")
    asset_url: str | None = Field(default=None, description="产物文件地址")
    cost: float = Field(default=0.0, description="本次生产费用")
    version: int = Field(default=1, description="产物版本")
    status: ProductionStatus = Field(
        default=ProductionStatus.PENDING, description="生产状态"
    )


class QuizSeed(BaseModel):
    """练习题种子。"""

    question: str = Field(..., description="题目文本")
    question_type: str = Field(default="mcq", description="题型")
    answer: str = Field(default="", description="答案")
    explanation: str = Field(default="", description="解析")


# ── 第四层：分镜 (Scene) ─────────────────────────────────


class SceneIR(BaseModel):
    """分镜 — 系统最小生产单元。"""

    scene_id: str = Field(default_factory=lambda: str(uuid4()), description="分镜 ID")
    order: int = Field(..., description="分镜序号")
    scene_type: SceneType = Field(..., description="画面类型")
    narration_text: str = Field(default="", description="口播讲稿")
    subtitle_text: str = Field(default="", description="字幕文本")
    visual_spec: VisualSpec = Field(default_factory=VisualSpec, description="画面规格")
    duration_strategy: DurationStrategy = Field(
        default=DurationStrategy.NARRATION_DRIVEN, description="时长策略"
    )
    transition: TransitionType = Field(
        default=TransitionType.FADE, description="转场效果"
    )
    kp_tags: list[str] = Field(default_factory=list, description="关联知识点标签")
    source_page: int | None = Field(default=None, description="来源页码")
    production_meta: ProductionMeta = Field(
        default_factory=ProductionMeta, description="生产元数据"
    )
    ssml_markers: list[dict] = Field(
        default_factory=list,
        description="SSML 语音标记: [{'type':'pause','duration':0.8,'position':42}]",
    )
    visual_direction: str = Field(
        default="",
        description="视觉指令（如'缓慢推近标题'、'高亮第3个要点'）",
    )


# ── 第三层：知识点 (KnowledgePoint) ──────────────────────


class KnowledgePointIR(BaseModel):
    """知识点。"""

    kp_id: str = Field(default_factory=lambda: str(uuid4()), description="知识点 ID")
    title: str = Field(..., description="知识点标题")
    key_points: list[str] = Field(default_factory=list, description="要点列表")
    tags: list[str] = Field(default_factory=list, description="标签")
    source_ref: str = Field(default="", description="来源引用")
    quiz_seeds: list[QuizSeed] = Field(default_factory=list, description="练习题种子")
    scenes: list[SceneIR] = Field(default_factory=list, description="分镜列表")


# ── 第二层：章节 (Chapter) ───────────────────────────────


class ChapterIR(BaseModel):
    """章节。"""

    chapter_id: str = Field(default_factory=lambda: str(uuid4()), description="章节 ID")
    title: str = Field(..., description="章节标题")
    order: int = Field(..., description="章节序号")
    source_pages: list[int] = Field(default_factory=list, description="来源页码范围")
    knowledge_points: list[KnowledgePointIR] = Field(
        default_factory=list, description="知识点列表"
    )


# ── 第一层：课程 (Course) ────────────────────────────────


class CourseIR(BaseModel):
    """课程脚本 IR — 顶层结构。

    四层结构: Course → Chapter → KnowledgePoint → Scene
    """

    course_id: str = Field(default_factory=lambda: str(uuid4()), description="课程 ID")
    title: str = Field(default="", description="课程标题")
    subject: str = Field(default="", description="学科")
    grade: str = Field(default="", description="年级")
    target_audience: str = Field(default="", description="目标受众")
    template: str = Field(default="micro_lecture", description="视频模板")
    style: str = Field(default="formal_academic", description="风格")
    version: int = Field(default=1, description="版本号")
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="创建时间",
    )
    chapters: list[ChapterIR] = Field(default_factory=list, description="章节列表")
    teaching_outline: dict = Field(
        default_factory=dict,
        description="教学大纲（Outline Agent 产出，含叙事弧线、策略、衔接）",
    )
