"""
Agent Training Module (Backward Compatibility Shim)

⚠️ DEPRECATED: This module has been moved to sage.libs.finetune.agent

Please update your imports:
    # Old (deprecated)
    from sage.tools.agent_training import AgentSFTTrainer, AgentSFTConfig

    # New (recommended)
    from sage.libs.finetune.agent import AgentSFTTrainer, AgentSFTConfig

This shim will be removed in a future version.
"""

import warnings

# Emit deprecation warning on import
warnings.warn(
    "sage.tools.agent_training is deprecated. Please use sage.libs.finetune.agent instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the new location for backward compatibility
from sage.libs.finetune.agent import (
    AgentDialogProcessor,
    AgentRewardConfig,
    AgentSFTConfig,
    AgentSFTTrainer,
    CoresetSelector,
    OnlineContinualLearner,
    ProcessedDialog,
    RLTrainingConfig,
)

__all__ = [
    "AgentSFTConfig",
    "RLTrainingConfig",
    "AgentRewardConfig",
    "AgentSFTTrainer",
    "CoresetSelector",
    "OnlineContinualLearner",
    "AgentDialogProcessor",
    "ProcessedDialog",
]
