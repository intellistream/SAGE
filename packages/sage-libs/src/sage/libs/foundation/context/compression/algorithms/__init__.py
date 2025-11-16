"""
Refiner算法实现
===============

包含各种SOTA上下文压缩算法的实现。
"""

from sage.libs.context.compression.algorithms.long_refiner import (
    LongRefinerAlgorithm,
)
from sage.libs.context.compression.algorithms.simple import (
    SimpleRefiner,
)

# 未来可以添加更多算法
# from sage.libs.context.compression.algorithms.ecorag import ECoRAGAlgorithm
# from sage.libs.context.compression.algorithms.xrag import xRAGAlgorithm

__all__ = [
    "LongRefinerAlgorithm",
    "SimpleRefiner",
]
