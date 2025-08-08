"""
日志记录模块
=========

提供自定义日志记录功能。

模块:
----
- custom_logger: 多输出目标的自定义日志记录器
- custom_formatter: IDE友好的日志格式化器

Examples:
--------
>>> from sage.utils.logging import CustomLogger
>>> 
>>> # 创建多输出日志记录器
>>> logger = CustomLogger([
...     ("console", "INFO"),
...     ("app.log", "DEBUG")
... ], name="MyApp", log_base_folder="./logs")
>>> 
>>> logger.info("应用启动")
"""

from .custom_logger import CustomLogger
from .custom_formatter import CustomFormatter

__all__ = [
    "CustomLogger",
    "CustomFormatter",
]
