"""
SAGE - Streaming Analytics and Graph Engine

SAGE内核提供分布式流处理和图计算能力。

主要模块:
- api: API接口层
- kernels: 核心内核功能
- utils: 工具和辅助功能
- examples: 示例代码
"""

__version__ = "1.0.0"
__author__ = "SAGE Team"

# 导入主要API
try:
    from .api import *
    from .utils import *
except ImportError:
    # 开发模式下的后备导入
    pass

__all__ = [
    '__version__',
    '__author__',
]
