"""
SAGE Kernel - 流式数据处理引擎和基础算子

提供：
- 数据流执行引擎：Environment, DataStream API
- 基础算子：MapOperator, FilterOperator, FlatMapOperator
- 运行时组件：JobManager, Scheduler
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
from . import api, operators

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "JobManagerClient",
    "api",
    "operators",
]
