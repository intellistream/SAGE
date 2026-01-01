"""
Scheduler Implementation Module.

This module contains various scheduling strategy implementations
for developer comparison experiments.

Configure scheduler at Environment level:
    env = LocalEnvironment(scheduler="fifo")
    env = LocalEnvironment(scheduler="load_aware")

Available strategies:
- FIFOScheduler: First-in-first-out (simplest baseline)
- LoadAwareScheduler: Resource-aware scheduling
- RandomScheduler: Random node selection (baseline)
- RoundRobinScheduler: Fair round-robin scheduling
- PriorityScheduler: Priority-based scheduling

Scheduler name mapping:
    "fifo"       -> FIFOScheduler
    "load_aware" -> LoadAwareScheduler
    "random"     -> RandomScheduler
    "round_robin"-> RoundRobinScheduler
    "priority"   -> PriorityScheduler
"""

from sage.kernel.scheduler.impl.priority_scheduler import PriorityScheduler
from sage.kernel.scheduler.impl.random_scheduler import RandomScheduler
from sage.kernel.scheduler.impl.resource_aware_scheduler import LoadAwareScheduler
from sage.kernel.scheduler.impl.round_robin_scheduler import RoundRobinScheduler
from sage.kernel.scheduler.impl.simple_scheduler import FIFOScheduler

# Scheduler registry (string -> class)
SCHEDULER_REGISTRY: dict[str, type] = {
    "fifo": FIFOScheduler,
    "load_aware": LoadAwareScheduler,
    "random": RandomScheduler,
    "round_robin": RoundRobinScheduler,
    "priority": PriorityScheduler,
}


def get_scheduler(name: str, **kwargs):
    """
    Get a scheduler instance by name.

    Args:
        name: Scheduler name (e.g., "fifo", "load_aware", "random")
        **kwargs: Scheduler initialization parameters

    Returns:
        Scheduler instance

    Example:
        scheduler = get_scheduler("load_aware", max_concurrent=20)
    """
    name_lower = name.lower()
    if name_lower not in SCHEDULER_REGISTRY:
        available = ", ".join(SCHEDULER_REGISTRY.keys())
        raise ValueError(f"Unknown scheduler: {name}. Available: {available}")

    return SCHEDULER_REGISTRY[name_lower](**kwargs)


__all__ = [
    "FIFOScheduler",
    "LoadAwareScheduler",
    "RandomScheduler",
    "RoundRobinScheduler",
    "PriorityScheduler",
    "SCHEDULER_REGISTRY",
    "get_scheduler",
]
