"""
SIAS Core - Sample Selection and Continual Learning

This module contains the core algorithms for SIAS:
- CoresetSelector: Sample selection strategies (loss_topk, diversity, hybrid)
- OnlineContinualLearner: Experience replay buffer with importance weighting
- SIASSample: Generic sample data type
"""

from .continual_learner import OnlineContinualLearner
from .coreset_selector import CoresetSelector, SelectionSummary
from .types import SampleProtocol, SIASSample, wrap_sample

__all__ = [
    "CoresetSelector",
    "SelectionSummary",
    "OnlineContinualLearner",
    "SIASSample",
    "SampleProtocol",
    "wrap_sample",
]
