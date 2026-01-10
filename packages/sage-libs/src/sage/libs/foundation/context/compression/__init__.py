"""Context compression algorithms for managing long contexts in LLMs.

This module provides simple compression algorithms. For advanced context compression
(Long-Refiner, REFORM, Provence), use the independent isage-refiner package:

    pip install isage-refiner

Note: ContextService has been moved to sage.middleware.components.sage_refiner
because it depends on RefinerService (L4 component).

Migration note (2026-01-10):
- Long-Refiner and related implementations have been moved to isage-refiner
- Use sage.middleware.components.sage_refiner for integration with SAGE
- Direct usage: from sage_refiner import LongRefiner  (after pip install isage-refiner)
"""

from sage.libs.foundation.context.compression.algorithms.simple import SimpleRefiner

__all__ = [
    "SimpleRefiner",
]
