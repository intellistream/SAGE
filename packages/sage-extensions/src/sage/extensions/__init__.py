"""
SAGE Extensions Module
======================

高性能C++扩展模块，提供队列管理和数据库功能。
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "IntelliStream Team"

# 尝试导入扩展模块，如果失败则提供fallback
try:
    from .sage_queue import *
except ImportError:
    import warnings
    warnings.warn("sage_queue C++ extension not available, using Python fallback")

try:
    from .sage_db import *
except ImportError:
    import warnings
    warnings.warn("sage_db C++ extension not available, using Python fallback")

# 公开的API
__all__ = [
    # 将由子模块填充
]
