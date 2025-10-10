"""Version information for sage-studio package."""

# 独立硬编码版本
__version__ = "0.1.5.2"
__author__ = "IntelliStream Team"
__email__ = "shuhao_zhang@hust.edu.cn"
__version_info__ = tuple(int(i) for i in __version__.split(".") if i.isdigit())

__all__ = ["__version__", "__version_info__", "__author__", "__email__"]
