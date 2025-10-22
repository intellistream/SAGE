"""
SAGE Kernel API - 用户友好的流处理API接口

这个模块提供了 SAGE 的核心 API，包括：
- 环境配置（LocalEnvironment, RemoteEnvironment）
- 函数定义（BatchFunction, SinkFunction, SourceFunction等）
- 数据流操作（DataStream）

示例：
    from sage.kernel.api import LocalEnvironment
    from sage.kernel.api.function import MapFunction, BatchFunction, SinkFunction
"""

# 导入主要 API 类
from .local_environment import LocalEnvironment
from .remote_environment import RemoteEnvironment

# 版本信息
try:
    from sage.kernel._version import __author__, __email__, __version__
except ImportError:
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "LocalEnvironment",
    "RemoteEnvironment",
]
