"""
SAGE Common Logging Utilities
"""

from .custom_formatter import CustomFormatter
from .custom_logger import CustomLogger


def get_logger(name=None):
    """获取一个CustomLogger实例

    Args:
        name: Logger名称，默认为None

    Returns:
        CustomLogger实例
    """
    return CustomLogger(outputs=[("console", "INFO")], name=name or __name__)


__all__ = ["CustomLogger", "CustomFormatter", "get_logger"]
