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
>>> from sage.common.utils.logging import CustomLogger, get_logger
>>> 
>>> # 创建多输出日志记录器
>>> logger = CustomLogger([
...     ("console", "INFO"),
...     ("app.log", "DEBUG")
... ], name="MyApp", log_base_folder="./logs")
>>> 
>>> logger.info("应用启动")
>>> 
>>> # 或者使用简便的get_logger函数
>>> logger = get_logger("MyApp")
>>> logger.info("简单日志记录")
"""

from .custom_logger import CustomLogger
from .custom_formatter import CustomFormatter

def get_logger(name: str = "SAGE", level: str = "INFO"):
    """
    获取一个简单的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        
    Returns:
        CustomLogger: 配置好的日志记录器
    """
    return CustomLogger([("console", level)], name=name)

__all__ = [
    "CustomLogger",
    "CustomFormatter", 
    "get_logger",
]
