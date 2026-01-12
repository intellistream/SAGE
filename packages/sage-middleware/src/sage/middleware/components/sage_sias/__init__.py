"""SIAS - Streaming Importance-Aware Agent System.

This middleware component provides sample importance and continual learning
capabilities for agent systems. It integrates with NeuroMem for memory-based
importance scoring and experience replay.

Core Components:
- CoresetSelector: Importance-aware sample selection (loss_topk, diversity, hybrid)
- OnlineContinualLearner: Experience replay with importance weighting
- SelectionSummary: Statistics for selection operations

Usage:
    from sage.middleware.components.sage_sias import (
        CoresetSelector,
        OnlineContinualLearner,
        SelectionSummary,
    )

    # Coreset selection
    selector = CoresetSelector(strategy="hybrid")
    selected = selector.select(samples, target_size=1000)

    # Continual learning with replay
    learner = OnlineContinualLearner(buffer_size=2048, replay_ratio=0.25)
    batch = learner.update_buffer(new_samples)

Future Components (planned):
- StreamingImportanceScorer: I(x) = α·L_grad + β·D_ctx + γ·T_exec
- ReflectiveMemoryStore: Experience storage with pattern extraction (uses NeuroMem)
- AdaptiveExecutor: Pre/post verification and localized replanning
- MultiAgentRouter: Task decomposition and agent collaboration

Note:
    SIAS is placed in sage-middleware (L4) rather than sage-libs (L3) because
    it depends on NeuroMem memory system and potentially SageVDB for
    importance-based retrieval.
"""

from sage.middleware.components.sage_sias.continual_learner import (
    OnlineContinualLearner,
)
from sage.middleware.components.sage_sias.coreset_selector import (
    CoresetSelector,
    SelectionSummary,
)
from sage.middleware.components.sage_sias.types import (
    SampleProtocol,
    SIASSample,
)

__all__ = [
    # Core components
    "CoresetSelector",
    "OnlineContinualLearner",
    "SelectionSummary",
    # Types
    "SIASSample",
    "SampleProtocol",
]
