"""
SAGE Kernel API - 用户友好的流处理API接口

Layer: L3 (Kernel - Public API)
Dependencies: sage.platform (L2), sage.common (L1)

这个模块提供了 SAGE 的核心 API，包括：
- 环境配置（LocalEnvironment, RemoteEnvironment）
- 数据流操作（DataStream）
- 函数定义（从 sage.common.core.functions 导入）
- 算子抽象（MapOperator, FilterOperator等）

Architecture:
- 提供用户友好的流式处理 API
- 内部使用 runtime 模块实现执行
- 支持本地和远程两种执行模式

示例：
    ```python
    from sage.kernel.api import LocalEnvironment
    from sage.common.core.functions import MapFunction, SinkFunction

    env = LocalEnvironment("my_app")
    stream = env.from_collection([1, 2, 3])
    stream.map(lambda x: x * 2).print()
    env.execute()
    ```
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
