"""
SAGE Common - 基础设施和共享组件

提供：
- core: 核心类型和异常
- components: 基础组件（embedding, vllm等）
- config: 配置管理
- utils: 通用工具函数
"""

from . import components, config, core, model_registry, utils
from ._version import __version__

__all__ = [
    "__version__",
    "components",
    "config", 
    "core",
    "model_registry",
    "utils",
]
