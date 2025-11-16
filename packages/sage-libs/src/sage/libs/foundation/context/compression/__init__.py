"""Context compression algorithms for managing long contexts in LLMs.

This module provides generic algorithms for compressing and managing context
in large language models to handle long conversations and documents.

Note: ContextService has been moved to sage.middleware.components.sage_refiner
because it depends on RefinerService (L4 component).
"""

from sage.libs.foundation.context.compression.algorithms.long_refiner import (
    LongRefinerAlgorithm,
)
from sage.libs.foundation.context.compression.algorithms.simple import SimpleRefiner
from sage.libs.foundation.context.compression.refiner import BaseRefiner

__all__ = [
    "BaseRefiner",
    "LongRefinerAlgorithm",
    "SimpleRefiner",
]
