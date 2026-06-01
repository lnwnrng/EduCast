---
name: ir-design
description: 当设计、修改或校验课程脚本中间表示（IR/DSL）时使用此技能。IR 是 EduCast 系统的核心枢纽——解析只产出 IR，生成只消费 IR。
---

# 课程脚本中间表示（IR）设计规范

## 概述
课程脚本 IR 是课影系统的**核心数据结构**——解析只负责产出 IR，生成只消费 IR。它是一份分层的结构化脚本，不绑定任何具体厂商，既能被机器消费、又能被教师校对。

## IR 四层结构

### 1. 课程层 (Course)
```json
{
  "course_id": "uuid",
  "title": "高等数学 - 导数的定义",
  "subject": "mathematics",
  "grade": "college_freshman",
  "target_audience": "理工科大一学生",
  "template": "micro_lecture",
  "style": "formal_academic",
  "version": 1,
  "created_at": "ISO8601",
  "chapters": []
}
```

### 2. 章节层 (Chapter)
```json
{
  "chapter_id": "uuid",
  "title": "第三章 导数与微分",
  "order": 1,
  "source_pages": [15, 22],
  "knowledge_points": []
}
```

### 3. 知识点层 (KnowledgePoint)
```json
{
  "kp_id": "uuid",
  "title": "导数的定义",
  "key_points": ["极限定义", "左右导数"],
  "tags": ["calculus", "derivative", "limit"],
  "source_ref": "教材 P.89",
  "quiz_seeds": [],
  "scenes": []
}
```

### 4. 分镜层 (Scene) — 最小生产单元
```json
{
  "scene_id": "uuid",
  "order": 1,
  "scene_type": "slide | formula_animation | digital_human | generative_clip",
  "narration_text": "口播讲稿文本...",
  "subtitle_text": "字幕文本...",
  "visual_spec": {
    "slide_ref": "slide_003.png",
    "latex_steps": ["f'(x) = \\lim_{\\Delta x \\to 0}..."],
    "image_refs": [],
    "gen_prompt": "数学课堂、简洁、粉笔风格",
    "pip_position": "bottom_right",
    "pip_size": "small"
  },
  "duration_strategy": "narration_driven",
  "transition": "fade",
  "kp_tags": ["derivative_definition"],
  "source_page": 17,
  "production_meta": {
    "provider": null,
    "asset_url": null,
    "cost": 0.0,
    "version": 1,
    "status": "pending"
  }
}
```

## scene_type 枚举值
| 类型 | 说明 | 成本 |
|------|------|------|
| `slide` | 课件页渲染（主体画面） | 免费 |
| `formula_animation` | manim 公式推导动画 | 免费（CPU） |
| `digital_human` | 数字人讲师口播 | 小额付费 |
| `generative_clip` | 文/图生视频 API | 按需付费 |

## 设计原则
1. **厂商无关** — IR 不包含任何特定 API 的字段，Provider 信息仅在 `production_meta` 中
2. **人可校对** — 字段命名清晰，教师在 UI 上可直接编辑
3. **机器可消费** — 严格 JSON Schema，可被流水线各环节直接解析
4. **版本可追溯** — 每次修改递增 version，保存 IR 快照
5. **时长由音频驱动** — `duration_strategy: narration_driven` 表示分镜时长由 TTS 音频长度决定

## 注意事项
- IR 修改后必须通过 JSON Schema 校验
- 新增字段需同步更新 Schema 和前端编辑器
- 导出/归档时包含 IR 快照，用于版本回溯
