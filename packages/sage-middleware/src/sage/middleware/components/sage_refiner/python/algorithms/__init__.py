"""
Refiner算法实现
===============

包含各种SOTA上下文压缩算法的实现。
"""

from sage.middleware.components.sage_refiner.python.algorithms.long_refiner import (
    LongRefinerAlgorithm,
)
from sage.middleware.components.sage_refiner.python.algorithms.simple import (
    SimpleRefiner,
)

# 未来可以添加更多算法
# from sage.middleware.components.sage_refiner.python.algorithms.ecorag import ECoRAGAlgorithm
# from sage.middleware.components.sage_refiner.python.algorithms.xrag import xRAGAlgorithm

__all__ = [
    "LongRefinerAlgorithm",
    "SimpleRefiner",
]
