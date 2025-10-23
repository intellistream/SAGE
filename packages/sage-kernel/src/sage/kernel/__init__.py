"""
SAGE Kernel - 流式数据处理引擎和基础算子

Layer: L3 (Kernel)
Dependencies: sage.platform (L2), sage.common (L1)

提供：
- 数据流执行引擎：Environment, DataStream API
- 基础算子：MapOperator, FilterOperator, FlatMapOperator
- 运行时组件：JobManager, Scheduler
- RPC通信实现：RPCQueue（注册到L2工厂）
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.kernel._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# 导出核心组件 - 直接从具体模块导入，避免循环
try:
    from sage.kernel.runtime.jobmanager_client import JobManagerClient
except ImportError:
    # 如果导入失败，提供一个占位符
    JobManagerClient = None
    import warnings

    warnings.warn(
        "JobManagerClient is not available. Some features may be limited.",
        ImportWarning,
    )

# 导出子模块
__layer__ = "L3"

from . import api, operators

# ============================================================================
# 架构关键：L3向L2注册实现（Factory Pattern）
# ============================================================================
# 在初始化时注册RPCQueue实现到sage-platform的工厂
# 这样L2层可以创建L3实例，但不需要直接导入L3代码
try:
    from sage.platform.queue import register_rpc_queue_factory
    from sage.kernel.runtime.communication.rpc import RPCQueue

    def _rpc_queue_factory(**kwargs):
        """RPC队列工厂函数 - 由L2调用创建L3实例"""
        return RPCQueue(**kwargs)

    register_rpc_queue_factory(_rpc_queue_factory)

except ImportError as e:
    import warnings
    warnings.warn(
        f"Failed to register RPC queue factory: {e}. "
        "RPC queue functionality will not be available.",
        ImportWarning,
    )

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "JobManagerClient",
    "api",
    "operators",
]
