# Fine-tune 功能架构调整建议

## 当前状况

Fine-tune 功能目前分布在不同层级：

```
当前位置:
L6 (Tools): sage-tools/src/sage/tools/finetune/  ← 当前实现
L6 (Studio): sage-studio/src/sage/studio/services/finetune_manager.py  ← Studio 集成
```

## 问题分析

### 为什么当前在 L6 (sage-tools)?

1. **历史原因**: 最初设计为 CLI 工具，供开发者使用
1. **依赖重**: 依赖 transformers, torch, peft 等外部库
1. **开发工具定位**: 被视为开发辅助工具，不是核心 runtime 功能

### 是否应该下沉到 L1/L2?

**建议: 保持在 L6，但重构接口设计**

#### 原因：

1. **依赖隔离** ✅

   - Fine-tune 依赖大量外部训练库 (transformers, peft, torch)
   - 这些不应该成为 L1/L2 的核心依赖
   - L1/L2 应该保持轻量级

1. **使用场景** ✅

   - Fine-tune 是**开发时**工具，不是**运行时**核心
   - 用户在开发阶段微调模型，部署时使用推理
   - 符合 L6 (Tools) 的定位

1. **架构清晰性** ✅

   - L1 (Common): 通用组件、服务基类
   - L2 (Platform): 平台服务、资源管理
   - L3 (Kernel/Libs): 核心算法、Pipeline
   - L6 (Tools): **开发工具**（包括微调、测试、分析等）

## 推荐架构方案

### 方案 A: 保持在 L6，优化接口 (推荐) ⭐

```python
# L6: sage-tools (开发工具层)
sage-tools/src/sage/tools/
├── finetune/           # Fine-tune 工具 (保留)
│   ├── trainer.py      # LoRA Trainer
│   ├── config.py       # 训练配置
│   ├── data.py         # 数据处理
│   └── cli.py          # CLI 接口
├── benchmark/          # 性能测试工具
├── profiler/           # 性能分析工具
└── dev.py              # 开发辅助工具

# L1: sage-common (只提供接口定义)
sage-common/src/sage/common/
└── interfaces/
    └── finetune.py     # Fine-tune 接口定义 (新增)
        class IFineTuneService(BaseService):
            def train(config) -> TrainingResult: ...
            def export_model() -> Path: ...
```

**优点**:

- ✅ 保持依赖隔离
- ✅ 符合分层架构
- ✅ L1 定义接口，L6 实现细节
- ✅ 最小改动

**实施步骤**:

1. 在 L1 添加 `IFineTuneService` 接口定义
1. L6 的 `LoRATrainer` 实现该接口
1. Studio 通过接口调用 (依赖注入)

### 方案 B: 拆分功能 (复杂)

```python
# L2: sage-platform (抽象训练服务)
sage-platform/src/sage/platform/
└── training/
    ├── service.py      # 抽象训练服务
    └── interfaces.py   # 训练接口定义

# L6: sage-tools (具体实现)
sage-tools/src/sage/tools/
└── finetune/
    ├── lora_trainer.py   # LoRA 具体实现
    └── adapters/         # 不同框架适配器
```

**缺点**:

- ❌ 过度设计
- ❌ 增加复杂度
- ❌ 收益不明显

## 具体改进建议

### 1. 添加接口层 (最小改动)

```python
# packages/sage-common/src/sage/common/interfaces/finetune.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

class IFineTuneService(ABC):
    """Fine-tune 服务接口"""

    @abstractmethod
    def train(self, config: dict[str, Any]) -> dict[str, Any]:
        """训练模型"""
        ...

    @abstractmethod
    def export_model(self, output_path: Path) -> Path:
        """导出模型"""
        ...

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """验证配置"""
        ...

# packages/sage-tools/src/sage/tools/finetune/trainer.py
from sage.common.interfaces.finetune import IFineTuneService

class LoRATrainer(IFineTuneService):  # 实现接口
    """LoRA 微调实现"""

    def train(self, config: dict[str, Any]) -> dict[str, Any]:
        # 现有实现
        ...
```

### 2. Studio 集成优化

```python
# packages/sage-studio/src/sage/studio/services/finetune_manager.py
from sage.common.interfaces.finetune import IFineTuneService

class FinetuneManager:
    def __init__(self, trainer: IFineTuneService):
        self.trainer = trainer  # 依赖注入

    def start_training(self, task_id: str):
        # 通过接口调用，不依赖具体实现
        result = self.trainer.train(config)
```

## 小模型推荐 (RTX 3060)

基于测试和社区反馈：

### 🥇 最佳选择

- **Qwen/Qwen2.5-Coder-1.5B-Instruct**
  - 参数: 1.5B
  - 显存: 6-8GB (8-bit 量化)
  - 训练时间: 2-4小时 (1000样本, 3 epochs)
  - 优势: 代码能力强，微调效果好

### 🥈 备选方案

- **Qwen/Qwen2.5-0.5B-Instruct**

  - 参数: 500M
  - 显存: 4-6GB
  - 训练时间: 1-2小时
  - 优势: 训练超快，适合快速实验

- **Qwen/Qwen2.5-1.5B-Instruct**

  - 参数: 1.5B
  - 显存: 6-8GB
  - 训练时间: 2-4小时
  - 优势: 通用对话能力

### ⚠️ 谨慎使用

- **Qwen/Qwen2.5-3B-Instruct**: 需要 10-12GB 显存（RTX 3060 勉强）
- **Qwen/Qwen2.5-7B-Instruct**: 需要 16-20GB 显存（需要 RTX 4090）

## 训练配置建议

```python
# RTX 3060 最优配置
from sage.tools.finetune import PresetConfigs

config = PresetConfigs.rtx_3060()
config.model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
config.load_in_8bit = True          # 使用 8-bit 量化
config.max_length = 1024            # 序列长度
config.per_device_train_batch_size = 1
config.gradient_accumulation_steps = 16
config.gradient_checkpointing = True # 节省显存
```

## 模型下载机制

### HuggingFace Hub 自动下载

所有 Qwen 模型都托管在 HuggingFace:

- 下载路径: `~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/`
- 自动处理: VLLMService 的 `auto_download=True` 会自动下载
- 代理设置: 可通过 `HF_ENDPOINT` 环境变量配置国内镜像

```bash
# 使用国内镜像加速下载
export HF_ENDPOINT=https://hf-mirror.com
```

## 总结

**保持 fine-tune 在 L6 (sage-tools)**，理由：

1. ✅ 符合架构分层原则（开发工具 vs 运行时核心）
1. ✅ 避免 L1/L2 引入重度训练依赖
1. ✅ 接口定义在 L1，实现在 L6，清晰分离

**小改进**:

1. 在 L1 添加 `IFineTuneService` 接口定义
1. Studio 通过接口调用，不直接依赖实现
1. 保持现有代码位置不变

**RTX 3060 用户建议**:

- 使用 `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- 启用 8-bit 量化 + 梯度检查点
- 训练时间 2-4 小时可接受
