"""
Agent Training Pipeline

Provides training infrastructure for Agent models including:
- SFT (Supervised Fine-Tuning) with tool-calling data
- RL (Reinforcement Learning) with DPO/PPO/GRPO
- Evaluation against agent benchmarks
"""

from .config import (
    AgentRewardConfig,
    AgentSFTConfig,
    RLTrainingConfig,
)
from .continual import CoresetSelector, OnlineContinualLearner
from .data_formatter import AgentSFTFormatter
from .dialog_processor import AgentDialogProcessor
from .evaluator import AgentTrainingEvaluator
from .reward_model import AgentRewardModel
from .sft_trainer import AgentSFTTrainer

__all__ = [
    # Config
    "AgentSFTConfig",
    "RLTrainingConfig",
    "AgentRewardConfig",
    # Data
    "AgentSFTFormatter",
    "AgentDialogProcessor",
    "AgentSFTTrainer",
    "CoresetSelector",
    "OnlineContinualLearner",
    # Training
    # "AgentSFTTrainer",  # TODO
    # "AgentRLTrainer",   # TODO
    # Evaluation
    "AgentRewardModel",
    "AgentTrainingEvaluator",
]
