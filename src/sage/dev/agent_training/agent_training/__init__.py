"""
Agent Training Pipeline

Provides training infrastructure for Agent models including:

Note: CoresetSelector and OnlineContinualLearner have been moved to sage.libs.sias.
They are re-exported here for backward compatibility.
"""

# SIAS components - re-exported for backward compatibility
# New code should import from sage.libs.sias directly

from .config import (
    AgentRewardConfig,
    AgentSFTConfig,
    RLTrainingConfig,
)
from .data_formatter import AgentSFTFormatter
from .dialog_processor import AgentDialogProcessor
from .evaluator import AgentTrainingEvaluator
from .reward_model import AgentRewardModel

__all__ = [
    # Config
    "AgentSFTConfig",
    "RLTrainingConfig",
    "AgentRewardConfig",
    # Data
    "AgentSFTFormatter",
    "AgentDialogProcessor",
    # SIAS components (re-exported for compatibility)
    # Training
    # "AgentSFTTrainer",  # Optional dependency (peft/trl)
    # "AgentRLTrainer",   # TODO
    # Evaluation
    "AgentRewardModel",
    "AgentTrainingEvaluator",
]
