---
name: pipeline-orchestration
description: 当开发视频生成流水线、异步任务编排、FFmpeg 合成等功能时使用此技能，定义了任务状态机、重试策略和合成规范。
---

# 视频生成流水线编排规范

## 概述
EduCast 的核心价值在于**教育视频生产流水线**的编排。本技能定义了从文档上传到视频成片的全链路编排规范。

## 任务状态机
```
待处理(PENDING)
  → 解析中(PARSING)
    → 编排中(SCRIPTING)
      → 待审核(REVIEWING) ← 人在环
        → 生成中(GENERATING) ← 并行子任务
          → 合成中(COMPOSING)
            → 完成(COMPLETED) / 失败(FAILED)
```

## 并行子任务（生成阶段）
生成阶段包含多个并行子任务，互不依赖：
1. **TTS 配音** — 为每个分镜生成旁白音频
2. **课件渲染** — 将课件页渲染为图片/视频底图
3. **公式动画** — manim 渲染 LaTeX 推导动画（CPU）
4. **数字人口播** — 云端 API 生成讲师片段
5. **生成式片段** — 文/图生视频 API 生成片头等

所有子任务完成后，进入合成阶段。

## FFmpeg 合成规范
```bash
# 基本合成命令模式
ffmpeg -i background.mp4 \                   # 底画面（课件/公式动画）
       -i narrator_audio.mp3 \               # 旁白音频
       -i digital_human.mp4 \                # 数字人画中画（可选）
       -vf "overlay=W-w-20:H-h-20" \         # 画中画位置
       -vf "subtitles=subtitle.srt" \         # 字幕叠加
       -vf "movie=watermark.png[wm];[in][wm]overlay=10:10" \  # 水印
       -c:v libx264 -preset medium \
       -c:a aac -b:a 128k \
       output.mp4
```

### 输出规格
- **分辨率**: 1920×1080 (1080p) 或 1280×720 (720p)
- **编码**: H.264 / AAC
- **帧率**: 30fps
- **字幕**: SRT / VTT 外挂或硬嵌
- **章节**: FFmpeg metadata 或独立章节文件

### 画中画位置预设
```
┌──────────────────┐
│                  │
│   课件/公式动画   │
│                  │
│            ┌────┐│
│            │数字││
│            │人  ││
│            └────┘│
└──────────────────┘
  bottom_right (默认)
```

## 可靠性机制

### 重试策略
```python
RETRY_CONFIG = {
    "max_retries": 3,
    "backoff_base": 2,        # 指数退避基数（秒）
    "backoff_max": 60,        # 最大等待（秒）
    "retry_on": [500, 502, 503, 504, "timeout", "rate_limit"]
}
```

### 幂等性
- 以**输入指纹（hash）** 作为幂等键
- 相同输入重复提交不会产生新的 API 调用和费用
- 已完成的子任务产物落库，整体重跑时自动跳过

### 断点续跑
- 每个子任务独立持久化状态
- 流水线重启时扫描子任务状态，只补跑失败/未完成项
- 不重复下载/生成已有产物

### 并发限流
- 尊重各 API 的 QPS/并发限制
- 使用令牌桶或信号量控制并发
- 按 Provider 独立配置限流参数

## 进度透出
- 任务状态实时写入数据库
- 前端通过轮询或 WebSocket 获取进度
- 每个子任务有独立进度（0-100%）
- 关键节点支持中断与人工修改

## 注意事项
- FFmpeg 命令组装使用 Python 封装，不手写 shell 字符串拼接
- 临时文件统一放在 `workspace/{task_id}/` 目录下
- 合成完成后清理临时文件（保留 IR 快照和最终产物）
- 所有文件路径使用绝对路径
