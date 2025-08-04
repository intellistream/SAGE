"""
SAGE Userspace Agents Community - 社区贡献代理

从 sage-plugins 迁移而来，包含社区贡献的插件和代理：
- 社区插件系统
- 第三方代理集成
- 扩展功能

这些是社区驱动的开源扩展功能。
"""

# 导入社区插件
try:
    from .longrefiner_fn import *
except ImportError as e:
    import warnings  
    warnings.warn(f"Some community plugins not available: {e}")

__all__ = [
    # 社区插件会通过各模块的 __all__ 导出
]
