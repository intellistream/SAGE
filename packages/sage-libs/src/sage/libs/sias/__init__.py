"""
SIAS: Streaming Importance-Aware Agent System

A framework for efficient agent training with streaming sample importance scoring
and adaptive execution. This module is designed to be extracted as an independent
repository in the future.

Core Components:
    - CoresetSelector: Intelligent sample selection for efficient training
    - OnlineContinualLearner: Experience replay with importance weighting
    - StreamingImportanceScorer: SSIS algorithm for sample prioritization (TODO)

Usage:
    from sage.libs.sias import CoresetSelector, OnlineContinualLearner

    # Sample selection
    selector = CoresetSelector(strategy="hybrid")
    selected = selector.select(samples, target_size=1000)

    # Continual learning with replay
    learner = OnlineContinualLearner(buffer_size=2048, replay_ratio=0.25)
    batch = learner.update_buffer(new_samples)

Future Components (Paper 2):
    - StreamingImportanceScorer: I(x) = α·L_grad + β·D_ctx + γ·T_exec
    - ReflectiveMemoryStore: Experience storage with pattern extraction
    - AdaptiveExecutor: Pre/post verification and localized replanning
    - MultiAgentRouter: Task decomposition and agent collaboration
"""

from .core import (
    CoresetSelector,
    OnlineContinualLearner,
    SelectionSummary,
)

__all__ = [
    # Core components (migrated from finetune/agent)
    "CoresetSelector",
    "OnlineContinualLearner",
    "SelectionSummary",
]

__version__ = "0.1.0"
