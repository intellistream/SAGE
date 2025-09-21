"""
SAGE - Streaming-Augmented Generative Execution
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.middleware._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.3.1"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# 导入主要组件
from sage.middleware.components.neuromem.micro_service.neuromem_vdb import \
    NeuroMemVDB

__all__ = ["NeuroMemVDB"]
