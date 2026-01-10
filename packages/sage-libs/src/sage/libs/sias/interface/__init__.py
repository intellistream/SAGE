"""SIAS interface exports."""

from sage.libs.sias.interface.base import ContinualLearner, CoresetSelector
from sage.libs.sias.interface.factory import (
    SiasRegistryError,
    create_learner,
    create_selector,
    list_learners,
    list_selectors,
    register_learner,
    register_selector,
)

__all__ = [
    # Base classes
    "ContinualLearner",
    "CoresetSelector",
    # Registry
    "SiasRegistryError",
    "register_learner",
    "register_selector",
    # Factory
    "create_learner",
    "create_selector",
    # Discovery
    "list_learners",
    "list_selectors",
]
