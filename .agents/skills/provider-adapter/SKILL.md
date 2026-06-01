---
name: provider-adapter
description: 当开发或扩展 Provider 适配层（LLM/TTS/数字人/视频生成 API 接入）时使用此技能，定义了统一接口设计、降级策略和成本控制规范。
---

# Provider 适配层开发规范

## 概述
Provider 适配层是 EduCast 的**防供应商锁定机制**，把所有外部生成能力抽象为统一接口，支持路由/降级/成本核算。这是答辩的工程亮点之一。

## 四类能力接口

### 1. LLM 文本生成 (`LLMProvider`)
- 用途: 脚本编排、分镜规划、出题、合规审核
- 首选: 智谱 GLM-4-Flash（免费）
- 备选: DeepSeek、通义千问 Qwen

### 2. TTS 配音 (`TTSProvider`)
- 用途: 旁白配音、分镜音频
- 首选: Edge-TTS（免费）
- 备选: 阿里云 TTS、火山引擎 TTS

### 3. 数字人口播 (`DigitalHumanProvider`)
- 用途: 讲师口播画中画
- 首选: 智影/蝉镜（小额付费）
- 备选: HeyGem（自建）
- 降级: 纯旁白 + 课件（无数字人）

### 4. 文/图生视频 (`VideoGenProvider`)
- 用途: 片头、概念演示
- 首选: CogVideoX-Flash（免费/极低价）
- 备选: 通义万相、可灵、海螺

## 统一接口设计
```python
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class ProviderResult(BaseModel):
    task_id: str
    status: str  # pending | processing | completed | failed
    result_url: Optional[str] = None
    cost: float = 0.0
    error_msg: Optional[str] = None

class BaseProvider(ABC):
    """所有 Provider 的抽象基类"""
    
    @abstractmethod
    async def submit(self, request: dict) -> str:
        """提交生成任务，返回 task_id"""
        ...
    
    @abstractmethod
    async def poll(self, task_id: str) -> ProviderResult:
        """轮询任务状态"""
        ...
    
    @abstractmethod
    async def get_result(self, task_id: str) -> ProviderResult:
        """获取最终结果"""
        ...
    
    @abstractmethod
    def estimate_cost(self, request: dict) -> float:
        """预估本次调用成本"""
        ...
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 标识名"""
        ...
```

## 路由策略
```python
class RoutingStrategy:
    FREE_FIRST = "free_first"       # 免费优先（毕设默认）
    COST_FIRST = "cost_first"       # 成本优先
    QUALITY_FIRST = "quality_first" # 质量优先
    AVAILABLE = "available"          # 额度可用性优先
```

## 降级链机制
每类能力配置降级链，首选失败自动切换：
```
数字人: 智影 → HeyGem → [降级] 纯旁白+课件
视频生成: CogVideoX-Flash → 通义万相 → [降级] 静态图片+转场
TTS: Edge-TTS → 阿里云TTS → [降级] 无音频（仅字幕）
LLM: GLM-4-Flash → DeepSeek → [降级] 模板填充
```

## 成本控制
1. **调用前预估**: `estimate_cost()` 在提交前计算预估费用
2. **配额检查**: 超过项目配额上限时拦截
3. **缓存复用**: 相同输入（讲稿/提示词/参数哈希）命中缓存直接复用
4. **调用记录**: 每次调用记录 Provider、用量、费用，汇总到监控面板

## 注意事项
- 新增 Provider 只需实现 `BaseProvider` 接口，无需修改上层代码
- API 密钥统一通过环境变量或配置文件管理，**禁止硬编码**
- 所有 Provider 调用必须设置超时时间
- 失败重试遵循指数退避策略
