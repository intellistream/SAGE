"""
SAGE - Streaming-Augmented Generative Execution
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# Export refiner module for imports - only if vllm is available
try:
    from . import refiner

    __all__ = ["refiner", "__version__", "__author__", "__email__"]
except ImportError:
    # vllm not available, skip refiner import
    __all__ = ["__version__", "__author__", "__email__"]
