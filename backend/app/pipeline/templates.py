"""视频模板注册表 — 定义不同教学视频模板的配色、风格和编排偏好。"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateColors:
    """模板配色方案。"""

    bg: tuple[int, int, int] = (248, 249, 251)
    header: tuple[int, int, int] = (24, 38, 66)
    title: tuple[int, int, int] = (24, 38, 66)
    body: tuple[int, int, int] = (45, 52, 64)
    accent: tuple[int, int, int] = (37, 99, 235)
    badge_bg: tuple[int, int, int] = (37, 99, 235)
    badge_fg: tuple[int, int, int] = (255, 255, 255)
    cover_bg: tuple[int, int, int] = (24, 38, 66)


@dataclass(frozen=True)
class TemplateConfig:
    """视频模板配置。"""

    name: str
    display_name: str
    description: str
    colors: TemplateColors = field(default_factory=TemplateColors)
    prompt_style: str = "严谨而亲切"
    scene_type_hint: str = ""
    visual_style: str = ""
    default_duration_range: tuple[int, int] = (600, 900)


# ── 模板注册表 ──────────────────────────────────────────────

MICRO_LECTURE = TemplateConfig(
    name="micro_lecture",
    display_name="微课",
    description="10-15 分钟知识点精讲，蓝白简约风格，适合单一概念深入讲解",
    colors=TemplateColors(
        bg=(248, 249, 251),
        header=(24, 38, 66),
        title=(24, 38, 66),
        body=(45, 52, 64),
        accent=(37, 99, 235),
        badge_bg=(37, 99, 235),
        badge_fg=(255, 255, 255),
        cover_bg=(24, 38, 66),
    ),
    prompt_style="严谨而亲切，语言精炼，注重核心概念的清晰传达",
    scene_type_hint="以 slide 为主，适当穿插 formula_animation，少量 digital_human",
    visual_style=(
        "clean minimalist composition, soft natural lighting, "
        "slow camera push-in, muted blue-white academic palette, 16:9"
    ),
    default_duration_range=(600, 900),
)

MOOC = TemplateConfig(
    name="mooc",
    display_name="慕课",
    description="30-45 分钟系统课程，深蓝学术风格，包含章节总结和丰富公式推导",
    colors=TemplateColors(
        bg=(240, 243, 248),
        header=(15, 23, 42),
        title=(15, 23, 42),
        body=(30, 41, 59),
        accent=(30, 64, 175),
        badge_bg=(30, 64, 175),
        badge_fg=(255, 255, 255),
        cover_bg=(15, 23, 42),
    ),
    prompt_style="系统深入，学术性强，注重知识体系的完整性和逻辑推导",
    scene_type_hint=(
        "均衡使用 slide 和 formula_animation，"
        "每个章节末尾添加一个 digital_human 做总结回顾，"
        "复杂概念用 generative_clip 辅助可视化"
    ),
    visual_style=(
        "polished academic cinematography, even studio lighting, "
        "deliberate camera movement, deep blue scholarly palette, 16:9"
    ),
    default_duration_range=(1800, 2700),
)

LAB_EXPERIMENT = TemplateConfig(
    name="lab_experiment",
    display_name="实验课",
    description="20-30 分钟实验操作演示，绿白活力风格，强调步骤引导和安全提示",
    colors=TemplateColors(
        bg=(245, 250, 245),
        header=(20, 60, 40),
        title=(20, 60, 40),
        body=(35, 65, 50),
        accent=(22, 163, 74),
        badge_bg=(22, 163, 74),
        badge_fg=(255, 255, 255),
        cover_bg=(20, 60, 40),
    ),
    prompt_style="操作引导式，步骤清晰，注重实验安全提示和操作细节说明",
    scene_type_hint=(
        "以 slide 展示实验步骤为主，"
        "多用 generative_clip 模拟实验过程，"
        "减少 formula_animation，适当使用 digital_human 做操作讲解"
    ),
    visual_style=(
        "bright clinical environment, crisp daylight, "
        "steady handheld camera, green-white clean palette, 16:9"
    ),
    default_duration_range=(1200, 1800),
)


TEMPLATE_REGISTRY: dict[str, TemplateConfig] = {
    "micro_lecture": MICRO_LECTURE,
    "mooc": MOOC,
    "lab_experiment": LAB_EXPERIMENT,
}


def get_template(name: str) -> TemplateConfig:
    """获取模板配置，未找到时返回默认微课模板。"""
    return TEMPLATE_REGISTRY.get(name, MICRO_LECTURE)
