"""
SAGE Agent Finetuning Module

针对 Agent 工具调用能力的专用微调模块，包含:
- AgentSFTTrainer: Agent 对话监督微调训练器
- CoresetSelector: 智能样本选择器
- OnlineContinualLearner: 在线持续学习模块
- AgentDialogProcessor: Agent 对话数据处理器

这些组件是难题4（高精度工具规划与调用）的核心实现。

使用示例:
    from sage.libs.finetune.agent import AgentSFTTrainer, AgentSFTConfig

    config = AgentSFTConfig(
        base_model="Qwen/Qwen2.5-7B-Instruct",
        use_coreset_selection=True,
        coreset_strategy="hybrid",
        use_online_continual=True,
    )

    trainer = AgentSFTTrainer(config)
    trainer.train()
"""

from .config import AgentRewardConfig, AgentSFTConfig, RLTrainingConfig
from .continual import CoresetSelector, OnlineContinualLearner
from .dialog_processor import AgentDialogProcessor, ProcessedDialog
from .trainer import AgentSFTTrainer


# 延迟导入较重的模块
def __getattr__(name):
    """延迟导入重量级模块"""
    if name == "AgentEvaluator":
        from .evaluator import AgentEvaluator

        return AgentEvaluator
    if name == "RewardModel":
        from .reward_model import RewardModel

        return RewardModel
    if name == "DataFormatter":
        from .data_formatter import DataFormatter

        return DataFormatter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 核心配置
    "AgentSFTConfig",
    "RLTrainingConfig",
    "AgentRewardConfig",
    # 训练组件
    "AgentSFTTrainer",
    "CoresetSelector",
    "OnlineContinualLearner",
    # 数据处理
    "AgentDialogProcessor",
    "ProcessedDialog",
    # 延迟导入
    "AgentEvaluator",
    "RewardModel",
    "DataFormatter",
]
