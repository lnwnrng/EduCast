---
name: git-conventions
description: 当进行 Git 操作（提交、分支、PR）时使用此技能，定义了提交信息格式、分支命名和版本管理规范。
---

# Git 版本管理规范

## Commit Message 格式
使用 **Conventional Commits** 规范：

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Type 枚举
| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(parser): 支持 PPTX 备注提取` |
| `fix` | Bug 修复 | `fix(tts): 修复 Edge-TTS 超时问题` |
| `refactor` | 重构 | `refactor(provider): 统一 Provider 接口` |
| `docs` | 文档 | `docs: 更新 IR Schema 说明` |
| `style` | 代码格式 | `style: Black 格式化` |
| `test` | 测试 | `test(pipeline): 添加合成流程单元测试` |
| `chore` | 构建/依赖 | `chore: 升级 FastAPI 到 0.115` |
| `perf` | 性能优化 | `perf(composer): 减少 FFmpeg 临时文件 IO` |

### Scope 建议
`parser` / `script` / `tts` / `digital-human` / `video-gen` / `composer` / `pipeline` / `provider` / `ir` / `api` / `frontend` / `db` / `auth` / `storage` / `config`

## 分支命名
```
main                    # 主分支（稳定可发布）
develop                 # 开发分支
feature/<scope>-<desc>  # 功能分支: feature/parser-pptx-support
fix/<scope>-<desc>      # 修复分支: fix/tts-timeout-handling
refactor/<desc>         # 重构分支: refactor/provider-interface
```

## 开发流程
1. 从 `develop` 创建 `feature/` 分支
2. 开发完成后 PR 到 `develop`
3. `develop` 稳定后合并到 `main`
4. 重要里程碑打 Tag: `v0.1.0-p1` (P1骨架)、`v0.2.0-p2` (P2生成能力)、`v1.0.0-p3` (P3完整系统)

## 注意事项
- **禁止**提交 API 密钥、.env 文件中的敏感信息
- `.gitignore` 包含: `__pycache__/`, `*.pyc`, `.env`, `node_modules/`, `dist/`, `workspace/`
- 每次提交前运行 lint 和格式化
