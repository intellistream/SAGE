"""
Formatting Utilities for SAGE

Provides unified formatting functions for sizes, durations, timestamps, etc.
"""

from datetime import datetime
from typing import Union


def format_size(size_bytes: int | float) -> str:
    """
    格式化文件/内存大小为人类可读格式

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串，如 "1.5 MB"

    Examples:
        >>> format_size(1024)
        '1.0 KB'
        >>> format_size(1536)
        '1.5 KB'
        >>> format_size(1048576)
        '1.0 MB'
    """
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_float < 1024:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024
    return f"{size_float:.1f} PB"


def format_size_compact(size_bytes: int | float) -> str:
    """
    格式化文件/内存大小为紧凑格式（无空格）

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串，如 "1.5MB"
    """
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_float < 1024:
            return f"{size_float:.1f}{unit}"
        size_float /= 1024
    return f"{size_float:.1f}PB"


def format_duration(seconds: float) -> str:
    """
    格式化持续时间为人类可读格式

    Args:
        seconds: 秒数

    Returns:
        格式化后的字符串，如 "1h 30m" 或 "45.2s"

    Examples:
        >>> format_duration(45.5)
        '45.5s'
        >>> format_duration(90)
        '1m 30s'
        >>> format_duration(3661)
        '1h 1m'
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_duration_verbose(seconds: float) -> str:
    """
    格式化持续时间为详细格式

    Args:
        seconds: 秒数

    Returns:
        格式化后的字符串，如 "1 hour 30 minutes"
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if secs == 0:
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        return (
            f"{minutes} minute{'s' if minutes > 1 else ''} {secs} second{'s' if secs > 1 else ''}"
        )
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if minutes == 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        return (
            f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"
        )


def format_timestamp(timestamp: Union[float, str, datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳为人类可读格式

    Args:
        timestamp: 时间戳（Unix时间戳、字符串或datetime对象）
        fmt: 输出格式，默认 "%Y-%m-%d %H:%M:%S"

    Returns:
        格式化后的时间字符串
    """
    if isinstance(timestamp, str):
        return timestamp
    elif isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        return str(timestamp)

    return dt.strftime(fmt)


def format_percentage(value: float, decimals: int = 1, is_decimal: bool = True) -> str:
    """
    格式化百分比

    Args:
        value: 百分比的数值。如果 is_decimal=True，则应为小数 (0.0 - 1.0)；如果 is_decimal=False，则应为百分比值 (0.0 - 100.0)。
        decimals: 小数位数
        is_decimal: 指示 value 是否为小数（True，默认）或已为百分比（False）

    Returns:
        格式化后的百分比字符串

    Examples:
        >>> format_percentage(0.85)
        '85.0%'
        >>> format_percentage(85, is_decimal=False)
        '85.0%'
    """
    if is_decimal:
        return f"{value * 100:.{decimals}f}%"
    else:
        return f"{value:.{decimals}f}%"


def format_count(count: int) -> str:
    """
    格式化大数字为人类可读格式

    Args:
        count: 数量

    Returns:
        格式化后的字符串，如 "1.5K" 或 "2.3M"
    """
    count_float = float(count)
    if count_float < 1000:
        return str(count)
    elif count_float < 1000000:
        return f"{count_float / 1000:.1f}K"
    elif count_float < 1000000000:
        return f"{count_float / 1000000:.1f}M"
    else:
        return f"{count_float / 1000000000:.1f}B"


__all__ = [
    "format_size",
    "format_size_compact",
    "format_duration",
    "format_duration_verbose",
    "format_timestamp",
    "format_percentage",
    "format_count",
]
