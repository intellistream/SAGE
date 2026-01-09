"""Backward compatibility layer for sage.libs.finetune.

This module provides backward compatibility after the finetune implementations
were externalized to the independent `sage-finetune` package.

**DEPRECATED**: Direct imports from this compatibility layer are deprecated.
Please use the external package directly:

    pip install isage-finetune
    from sage_finetune import LoRATrainer, TrainingConfig, ...

**Migration Guide**:

Old import (deprecated):
    from sage.libs.finetune import LoRATrainer, TrainingConfig

New import (recommended):
    from sage_finetune import LoRATrainer, TrainingConfig

**Why was finetune externalized?**

1. **Modularity**: LLM fine-tuning toolkit is now independently maintained
2. **Reusability**: Can be used outside SAGE ecosystem
3. **Faster iteration**: Independent release cycle for fine-tuning features
4. **Reduced coupling**: Clean separation from sage-libs core

**Features** (in sage-finetune):
- LoRA fine-tuning with PEFT
- 4-bit/8-bit quantization with bitsandbytes
- Agent trajectory training and evaluation
- Multi-task training support
- Reward model training
- CLI interface with Typer
- TensorBoard and Wandb integration

**Repository**: https://github.com/intellistream/sage-finetune
**PyPI**: https://pypi.org/project/isage-finetune/
"""

import warnings

warnings.warn(
    "Importing from 'sage.libs.finetune' is deprecated. "
    "Please install 'isage-finetune' and import directly: "
    "'from sage_finetune import ...'",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from sage_finetune import (
        AgentConfig,
        # Agent training
        AgentTrajectoryTrainer,
        # Engine
        FinetuneEngine,
        # Manager
        FinetuneManager,
        LoRAConfig,
        # Core training
        LoRATrainer,
        MultiTaskTrainer,
        PresetConfigs,
        RewardModelTrainer,
        TrainingConfig,
        # CLI
        cli_app,
        load_dataset_from_config,
        # Data
        prepare_dataset,
    )

    __all__ = [
        "LoRATrainer",
        "TrainingConfig",
        "LoRAConfig",
        "PresetConfigs",
        "FinetuneManager",
        "prepare_dataset",
        "load_dataset_from_config",
        "FinetuneEngine",
        "cli_app",
        "AgentTrajectoryTrainer",
        "AgentConfig",
        "MultiTaskTrainer",
        "RewardModelTrainer",
    ]

except ImportError as e:
    raise ImportError(
        f"Failed to import from 'sage_finetune'. "
        f"Please install the package:\n\n"
        f"    pip install isage-finetune\n\n"
        f"Or install sage-libs with finetune support:\n\n"
        f"    pip install 'isage-libs[finetune]'\n\n"
        f"Repository: https://github.com/intellistream/sage-finetune\n"
        f"Original error: {e}"
    ) from e
