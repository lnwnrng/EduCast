"""IR 校验工具 — 验证课程脚本 IR 的完整性与一致性。"""

from app.ir.schema import CourseIR, SceneType


def validate_ir(ir: CourseIR) -> list[str]:
    """校验 IR 完整性。

    Returns:
        验证错误列表（空列表表示通过）。
    """
    errors: list[str] = []

    if not ir.title:
        errors.append("课程标题不能为空")

    if not ir.chapters:
        errors.append("课程至少包含一个章节")
        return errors

    for ch_idx, chapter in enumerate(ir.chapters):
        if not chapter.title:
            errors.append(f"章节 #{ch_idx + 1} 标题不能为空")

        if not chapter.knowledge_points:
            errors.append(f"章节 '{chapter.title}' 至少包含一个知识点")
            continue

        for kp_idx, kp in enumerate(chapter.knowledge_points):
            if not kp.title:
                errors.append(
                    f"章节 '{chapter.title}' 知识点 #{kp_idx + 1} 标题不能为空"
                )

            if not kp.scenes:
                errors.append(f"知识点 '{kp.title}' 至少包含一个分镜")
                continue

            # 校验分镜序号连续性
            expected_order = 1
            for scene in kp.scenes:
                if scene.order != expected_order:
                    errors.append(
                        f"知识点 '{kp.title}' 分镜序号不连续："
                        f"期望 {expected_order}，实际 {scene.order}"
                    )
                expected_order += 1

                # 校验分镜内容
                if not scene.narration_text:
                    errors.append(f"分镜 '{scene.scene_id}' 旁白文本不能为空")

                # 校验画面规格与类型匹配
                if (
                    scene.scene_type == SceneType.SLIDE
                    and not scene.visual_spec.slide_ref
                ):
                    errors.append(
                        f"分镜 '{scene.scene_id}' 类型为 slide 但缺少 slide_ref"
                    )

                if (
                    scene.scene_type == SceneType.FORMULA_ANIMATION
                    and not scene.visual_spec.latex_steps
                ):
                    errors.append(
                        f"分镜 '{scene.scene_id}' 类型为 formula_animation "
                        f"但缺少 latex_steps"
                    )

    return errors
