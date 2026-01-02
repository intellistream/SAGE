"""
SAGE Finetune - 轻量级大模型微调工具

这是一个独立的微调模块，可以作为 SAGE 生态的一部分使用，
也可以被其他项目引用。

主要特性:
- LoRA 微调
- 量化训练 (8-bit/4-bit)
- 混合精度训练
- 梯度检查点
- TensorBoard/Wandb 集成
- 支持多种数据格式

使用示例:
    from sage.libs.finetune import LoRATrainer, TrainingConfig

    config = TrainingConfig(
        model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        output_dir="./output",
        num_epochs=3,
    )

    trainer = LoRATrainer(config)
    trainer.train(dataset)
"""

# 延迟导入：只在实际使用时才加载 transformers 等重量级依赖
# 这对于 CLI --help 等轻量级操作很重要

from .cli import app  # CLI 应用
from .config import LoRAConfig, PresetConfigs, TrainingConfig
from .data import load_training_data, prepare_dataset
from .engine import (  # Control Plane integration (L3 implementation)
    FinetuneConfig,
    FinetuneEngine,
)
from .manager import (  # Studio backend components (moved from L6 to L3)
    FinetuneManager,
    FinetuneStatus,
    FinetuneTask,
    check_gpu_resources,
    finetune_manager,  # Global singleton instance
)


# LoRATrainer 延迟导入，使用 __getattr__
def __getattr__(name):
    """延迟导入 LoRATrainer，避免在模块加载时就导入 transformers"""
    if name == "LoRATrainer":
        from .trainer import LoRATrainer

        return LoRATrainer
    if name == "agent":
        from . import agent

        return agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 核心训练类（延迟导入）
    "LoRATrainer",  # type: ignore[attr-defined]
    # 配置类（轻量级，直接导入）
    "TrainingConfig",
    "LoRAConfig",
    "PresetConfigs",
    # 数据处理（轻量级，直接导入）
    "prepare_dataset",
    "load_training_data",
    # CLI 应用
    "app",
    # Agent 微调子模块（延迟导入）
    "agent",  # type: ignore[attr-defined]
    # Studio backend components (moved from L6 to L3)
    "FinetuneManager",
    "FinetuneStatus",
    "FinetuneTask",
    "finetune_manager",  # Global singleton
    "check_gpu_resources",
]

__version__ = "0.1.0"
