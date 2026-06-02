"""IR Schema 校验测试。

覆盖:
  - CourseIR 四层结构构建
  - 各枚举值
  - 默认值
  - validate_ir 校验规则
"""

from app.ir.schema import (
    ChapterIR,
    CourseIR,
    DurationStrategy,
    KnowledgePointIR,
    PipPosition,
    PipSize,
    ProductionMeta,
    ProductionStatus,
    QuizSeed,
    SceneIR,
    SceneType,
    TransitionType,
    VisualSpec,
)
from app.ir.validator import validate_ir

# ── CourseIR 构建测试 ────────────────────────────────────


class TestCourseIR:
    """课程 IR 数据结构测试。"""

    def test_create_empty_course(self) -> None:
        """创建空课程 IR。"""
        ir = CourseIR(title="测试课程")
        assert ir.title == "测试课程"
        assert ir.chapters == []
        assert ir.version == 1
        assert ir.course_id  # 自动生成 UUID

    def test_create_full_course(self) -> None:
        """创建包含完整四层结构的课程 IR。"""
        scene = SceneIR(
            order=1,
            scene_type=SceneType.SLIDE,
            narration_text="这是一段旁白",
            subtitle_text="字幕文本",
            visual_spec=VisualSpec(
                slide_ref="slide_1.png",
            ),
        )
        kp = KnowledgePointIR(
            title="导数的定义",
            key_points=["极限定义", "几何意义"],
            scenes=[scene],
        )
        chapter = ChapterIR(
            title="第一章 导数",
            order=1,
            source_pages=[1, 2, 3],
            knowledge_points=[kp],
        )
        ir = CourseIR(
            title="高等数学",
            subject="mathematics",
            chapters=[chapter],
        )

        assert ir.title == "高等数学"
        assert len(ir.chapters) == 1
        assert ir.chapters[0].title == "第一章 导数"
        assert len(ir.chapters[0].knowledge_points) == 1
        assert ir.chapters[0].knowledge_points[0].title == "导数的定义"
        assert len(ir.chapters[0].knowledge_points[0].scenes) == 1

    def test_course_id_auto_generated(self) -> None:
        """课程 ID 自动生成且唯一。"""
        ir1 = CourseIR(title="A")
        ir2 = CourseIR(title="B")
        assert ir1.course_id != ir2.course_id

    def test_scene_id_auto_generated(self) -> None:
        """分镜 ID 自动生成且唯一。"""
        s1 = SceneIR(order=1, scene_type=SceneType.SLIDE)
        s2 = SceneIR(order=2, scene_type=SceneType.SLIDE)
        assert s1.scene_id != s2.scene_id


# ── 枚举测试 ─────────────────────────────────────────────


class TestEnums:
    """枚举值测试。"""

    def test_scene_types(self) -> None:
        """所有分镜类型。"""
        assert SceneType.SLIDE == "slide"
        assert SceneType.FORMULA_ANIMATION == "formula_animation"
        assert SceneType.DIGITAL_HUMAN == "digital_human"
        assert SceneType.GENERATIVE_CLIP == "generative_clip"

    def test_duration_strategies(self) -> None:
        """时长策略。"""
        assert DurationStrategy.NARRATION_DRIVEN == "narration_driven"
        assert DurationStrategy.FIXED == "fixed"
        assert DurationStrategy.AUTO == "auto"

    def test_transition_types(self) -> None:
        """转场类型。"""
        assert TransitionType.FADE == "fade"
        assert TransitionType.CUT == "cut"
        assert TransitionType.DISSOLVE == "dissolve"

    def test_pip_positions(self) -> None:
        """画中画位置。"""
        assert PipPosition.BOTTOM_RIGHT == "bottom_right"
        assert PipPosition.FULL_SCREEN == "full_screen"

    def test_production_status(self) -> None:
        """生产状态。"""
        assert ProductionStatus.PENDING == "pending"
        assert ProductionStatus.COMPLETED == "completed"
        assert ProductionStatus.FAILED == "failed"


# ── 默认值测试 ───────────────────────────────────────────


class TestDefaults:
    """默认值测试。"""

    def test_scene_defaults(self) -> None:
        """分镜默认值。"""
        scene = SceneIR(order=1, scene_type=SceneType.SLIDE)
        assert scene.narration_text == ""
        assert scene.subtitle_text == ""
        assert scene.duration_strategy == DurationStrategy.NARRATION_DRIVEN
        assert scene.transition == TransitionType.FADE
        assert scene.kp_tags == []
        assert scene.source_page is None

    def test_visual_spec_defaults(self) -> None:
        """画面规格默认值。"""
        spec = VisualSpec()
        assert spec.slide_ref is None
        assert spec.latex_steps == []
        assert spec.image_refs == []
        assert spec.gen_prompt is None
        assert spec.pip_position == PipPosition.BOTTOM_RIGHT
        assert spec.pip_size == PipSize.SMALL

    def test_production_meta_defaults(self) -> None:
        """生产元数据默认值。"""
        meta = ProductionMeta()
        assert meta.provider is None
        assert meta.asset_url is None
        assert meta.cost == 0.0
        assert meta.version == 1
        assert meta.status == ProductionStatus.PENDING

    def test_course_defaults(self) -> None:
        """课程默认值。"""
        ir = CourseIR()
        assert ir.title == ""
        assert ir.subject == ""
        assert ir.template == "micro_lecture"
        assert ir.style == "formal_academic"
        assert ir.version == 1

    def test_quiz_seed(self) -> None:
        """练习题种子。"""
        quiz = QuizSeed(question="什么是导数？")
        assert quiz.question_type == "mcq"
        assert quiz.answer == ""
        assert quiz.explanation == ""


# ── JSON 序列化测试 ──────────────────────────────────────


class TestSerialization:
    """序列化与反序列化测试。"""

    def test_course_ir_roundtrip(self) -> None:
        """CourseIR JSON 往返。"""
        ir = CourseIR(
            title="测试",
            chapters=[
                ChapterIR(
                    title="章节1",
                    order=1,
                    knowledge_points=[
                        KnowledgePointIR(
                            title="KP1",
                            scenes=[
                                SceneIR(
                                    order=1,
                                    scene_type=SceneType.SLIDE,
                                    narration_text="旁白",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

        # 序列化
        json_str = ir.model_dump_json()
        assert json_str

        # 反序列化
        ir2 = CourseIR.model_validate_json(json_str)
        assert ir2.title == ir.title
        assert len(ir2.chapters) == 1
        assert ir2.chapters[0].knowledge_points[0].scenes[0].narration_text == "旁白"

    def test_model_dump(self) -> None:
        """model_dump 输出字典。"""
        scene = SceneIR(
            order=1,
            scene_type=SceneType.SLIDE,
            narration_text="测试",
        )
        d = scene.model_dump()
        assert d["order"] == 1
        assert d["scene_type"] == "slide"
        assert d["narration_text"] == "测试"


# ── IR 校验器测试 ────────────────────────────────────────


class TestIRValidator:
    """IR 校验规则测试。"""

    def _make_valid_ir(self) -> CourseIR:
        """创建一个有效的 IR。"""
        return CourseIR(
            title="有效课程",
            chapters=[
                ChapterIR(
                    title="第一章",
                    order=1,
                    knowledge_points=[
                        KnowledgePointIR(
                            title="知识点1",
                            scenes=[
                                SceneIR(
                                    order=1,
                                    scene_type=SceneType.SLIDE,
                                    narration_text="旁白内容",
                                    visual_spec=VisualSpec(slide_ref="slide_1.png"),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    def test_valid_ir_passes(self) -> None:
        """有效 IR 通过校验。"""
        ir = self._make_valid_ir()
        errors = validate_ir(ir)
        assert errors == []

    def test_empty_title_fails(self) -> None:
        """空标题校验失败。"""
        ir = self._make_valid_ir()
        ir.title = ""
        errors = validate_ir(ir)
        assert any("标题" in e for e in errors)

    def test_no_chapters_fails(self) -> None:
        """无章节校验失败。"""
        ir = CourseIR(title="测试", chapters=[])
        errors = validate_ir(ir)
        assert any("章节" in e for e in errors)

    def test_empty_chapter_title_fails(self) -> None:
        """空章节标题校验失败。"""
        ir = self._make_valid_ir()
        ir.chapters[0].title = ""
        errors = validate_ir(ir)
        assert any("标题" in e for e in errors)

    def test_no_knowledge_points_fails(self) -> None:
        """章节无知识点校验失败。"""
        ir = CourseIR(
            title="测试",
            chapters=[
                ChapterIR(
                    title="空章节",
                    order=1,
                    knowledge_points=[],
                ),
            ],
        )
        errors = validate_ir(ir)
        assert any("知识点" in e for e in errors)

    def test_no_scenes_fails(self) -> None:
        """知识点无分镜校验失败。"""
        ir = CourseIR(
            title="测试",
            chapters=[
                ChapterIR(
                    title="章节",
                    order=1,
                    knowledge_points=[
                        KnowledgePointIR(
                            title="知识点",
                            scenes=[],
                        ),
                    ],
                ),
            ],
        )
        errors = validate_ir(ir)
        assert any("分镜" in e for e in errors)

    def test_scene_order_discontinuity(self) -> None:
        """分镜序号不连续校验失败。"""
        ir = CourseIR(
            title="测试",
            chapters=[
                ChapterIR(
                    title="章节",
                    order=1,
                    knowledge_points=[
                        KnowledgePointIR(
                            title="知识点",
                            scenes=[
                                SceneIR(
                                    order=1,
                                    scene_type=SceneType.SLIDE,
                                    narration_text="旁白1",
                                    visual_spec=VisualSpec(slide_ref="s1.png"),
                                ),
                                SceneIR(
                                    order=3,  # 跳过了 2
                                    scene_type=SceneType.SLIDE,
                                    narration_text="旁白3",
                                    visual_spec=VisualSpec(slide_ref="s3.png"),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        errors = validate_ir(ir)
        assert any("序号不连续" in e for e in errors)

    def test_slide_without_slide_ref(self) -> None:
        """slide 类型缺少 slide_ref 校验失败。"""
        ir = CourseIR(
            title="测试",
            chapters=[
                ChapterIR(
                    title="章节",
                    order=1,
                    knowledge_points=[
                        KnowledgePointIR(
                            title="知识点",
                            scenes=[
                                SceneIR(
                                    order=1,
                                    scene_type=SceneType.SLIDE,
                                    narration_text="旁白",
                                    visual_spec=VisualSpec(),  # 无 slide_ref
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        errors = validate_ir(ir)
        assert any("slide_ref" in e for e in errors)

    def test_formula_without_latex_steps(self) -> None:
        """formula_animation 缺少 latex_steps 校验失败。"""
        ir = CourseIR(
            title="测试",
            chapters=[
                ChapterIR(
                    title="章节",
                    order=1,
                    knowledge_points=[
                        KnowledgePointIR(
                            title="知识点",
                            scenes=[
                                SceneIR(
                                    order=1,
                                    scene_type=SceneType.FORMULA_ANIMATION,
                                    narration_text="旁白",
                                    visual_spec=VisualSpec(),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        errors = validate_ir(ir)
        assert any("latex_steps" in e for e in errors)

    def test_empty_narration_fails(self) -> None:
        """空旁白校验失败。"""
        ir = CourseIR(
            title="测试",
            chapters=[
                ChapterIR(
                    title="章节",
                    order=1,
                    knowledge_points=[
                        KnowledgePointIR(
                            title="知识点",
                            scenes=[
                                SceneIR(
                                    order=1,
                                    scene_type=SceneType.SLIDE,
                                    narration_text="",  # 空旁白
                                    visual_spec=VisualSpec(slide_ref="s.png"),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        errors = validate_ir(ir)
        assert any("旁白" in e for e in errors)
