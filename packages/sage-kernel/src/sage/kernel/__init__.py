"""
SAGE - Streaming-Augmented Generative Execution
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.kernel._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.3.1"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# 导出核心组件
try:
    from .jobmanager.jobmanager_client import JobManagerClient
except ImportError:
    # 如果导入失败，使用兼容性层
    try:
        from sage.core.api.compatibility import safe_import_jobmanager_client

        JobManagerClient = safe_import_jobmanager_client()
    except ImportError:
        # 最后的备用方案
        class JobManagerClient:
            def __init__(self, *args, **kwargs):
                raise ImportError(
                    "JobManagerClient is not available. Please check your installation."
                )


__all__ = ["__version__", "__author__", "__email__", "JobManagerClient"]
