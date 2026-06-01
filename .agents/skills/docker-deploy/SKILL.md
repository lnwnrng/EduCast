---
name: docker-deploy
description: 当构建 Docker 镜像、编写 docker-compose 或处理部署相关事务时使用此技能。
---

# Docker 部署规范

## 概述
EduCast 使用 Docker + docker-compose 单机部署，**不需要 GPU 服务器**。所有重计算（视频生成/数字人/TTS）都在云端 API 完成，本地只需运行后端 + FFmpeg（CPU）。

## docker-compose 架构
```yaml
services:
  backend:          # FastAPI 后端
  celery-worker:    # Celery Worker（选做）
  redis:            # 缓存/消息队列（如用 Celery）
  frontend:         # React 前端（Nginx 托管）
```

## 毕设简化方案
毕设阶段可不上完整 docker-compose，直接用：
- `uvicorn app.main:app --reload` 运行后端
- `npm run dev` 运行前端
- SQLite 本地文件数据库
- 本地文件系统存储

## Dockerfile 约定
```dockerfile
# 后端
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg
# ... 安装依赖

# 前端
FROM node:20-slim AS builder
# ... 构建
FROM nginx:alpine
# ... 部署
```

## 环境变量管理
```env
# .env.example（提交到仓库，不含真实值）
DATABASE_URL=sqlite:///./educast.db
REDIS_URL=redis://localhost:6379/0

# Provider API Keys
GLM_API_KEY=
DEEPSEEK_API_KEY=
EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural
COGVIDEO_API_KEY=
DIGITAL_HUMAN_API_KEY=

# 成本配额
MAX_COST_PER_TASK=10.0
MAX_COST_PER_PROJECT=100.0
```

## 注意事项
- `.env` 文件**禁止**提交到 Git
- 提供 `.env.example` 作为模板
- FFmpeg 必须安装在后端容器中
- manim 依赖 LaTeX，后端容器需安装 `texlive-latex-base`
