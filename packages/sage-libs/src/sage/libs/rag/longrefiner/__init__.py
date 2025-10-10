"""
LongRefiner - 向后兼容模块
=========================

注意: 核心实现已迁移到 sage.middleware.components.sage_refiner
      本模块仅提供向后兼容的别名。

推荐使用:
    from sage.libs.rag.refiner import RefinerOperator
    
向后兼容:
    from sage.libs.rag.longrefiner import LongRefinerAdapter  # 仍然可用
"""

from sage.libs.rag.refiner import RefinerOperator

# 向后兼容别名
LongRefinerAdapter = RefinerOperator

__all__ = ["LongRefinerAdapter", "RefinerOperator"]
