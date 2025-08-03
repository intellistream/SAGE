"""
SAGE Extensions Module
======================

高性能C++扩展模块，提供队列管理和数据库功能。
"""

import warnings
from typing import List, Optional

# 版本信息
__version__ = "1.0.0"
__author__ = "IntelliStream Team"

# 导入状态跟踪
_extensions_loaded = {
    'sage_queue': False,
    'sage_db': False,
}

# 尝试导入扩展模块，如果失败则提供fallback
try:
    from .sage_queue import *
    _extensions_loaded['sage_queue'] = True
except ImportError as e:
    warnings.warn(f"sage_queue C++ extension not available: {e}")

try:
    from .sage_db import *
    _extensions_loaded['sage_db'] = True
except ImportError as e:
    warnings.warn(f"sage_db C++ extension not available: {e}")

def get_extension_status() -> dict:
    """获取扩展加载状态"""
    return _extensions_loaded.copy()

def check_extensions() -> bool:
    """检查所有扩展是否正常加载"""
    return all(_extensions_loaded.values())

# 公开的API
__all__ = [
    'get_extension_status',
    'check_extensions',
    # 其他API将由子模块动态添加
]
