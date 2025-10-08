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
    from sage.tools.finetune import LoRATrainer, TrainingConfig
    
    config = TrainingConfig(
        model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        output_dir="./output",
        num_epochs=3,
    )
    
    trainer = LoRATrainer(config)
    trainer.train(dataset)
"""

from .trainer import LoRATrainer
from .config import TrainingConfig, LoRAConfig, PresetConfigs
from .data import prepare_dataset, load_training_data
from .cli import app  # CLI 应用

__all__ = [
    # 核心训练类
    "LoRATrainer",
    "TrainingConfig",
    "LoRAConfig",
    "PresetConfigs",
    # 数据处理
    "prepare_dataset",
    "load_training_data",
    # CLI 应用
    "app",
]

__version__ = "0.1.0"

__all__ = [
    "LoRATrainer",
    "TrainingConfig",
    "LoRAConfig",
    "PresetConfigs",
    "prepare_dataset",
    "load_training_data",
]
