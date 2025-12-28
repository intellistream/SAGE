#!/usr/bin/env python3
"""
SAGE CLI Output Formatter
=========================

统一的输出格式化和显示功能
"""

import json
from datetime import datetime
from typing import Any

from sage.common.utils.formatting import (
    format_duration as _format_duration,
)
from sage.common.utils.formatting import (
    format_size_compact as _format_size_compact,
)
from sage.common.utils.formatting import (
    format_timestamp as _format_timestamp,
)

try:
    from colorama import Back, Fore, Style, init  # type: ignore[import-untyped]
    from tabulate import tabulate  # type: ignore[import-untyped]

    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

    # 提供基础的颜色类
    class _ForeColors:
        GREEN = RED = YELLOW = BLUE = CYAN = MAGENTA = WHITE = ""

    class _BackColors:
        GREEN = RED = YELLOW = BLUE = CYAN = MAGENTA = WHITE = ""

    class _StyleColors:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""

    Fore = _ForeColors()
    Back = _BackColors()
    Style = _StyleColors()


class Colors:
    """终端颜色常量"""

    if COLORAMA_AVAILABLE:
        GREEN = Fore.GREEN
        RED = Fore.RED
        YELLOW = Fore.YELLOW
        BLUE = Fore.BLUE
        CYAN = Fore.CYAN
        MAGENTA = Fore.MAGENTA
        WHITE = Fore.WHITE
        BOLD = Style.BRIGHT
        DIM = Style.DIM
        RESET = Style.RESET_ALL
    else:
        GREEN = RED = YELLOW = BLUE = CYAN = MAGENTA = WHITE = BOLD = DIM = RESET = ""


class OutputFormatter:
    """统一的输出格式化器"""

    def __init__(self, colors: bool = True, format_type: str = "table"):
        self.colors = colors and COLORAMA_AVAILABLE
        self.format_type = format_type

    def print_message(self, message: str, msg_type: str = "info", prefix: str | None = None):
        """
        打印格式化消息

        Args:
            message: 消息内容
            msg_type: 消息类型 (info, success, error, warning)
            prefix: 可选前缀
        """
        if not self.colors:
            if prefix:
                print(f"{prefix} {message}")
            else:
                print(message)
            return

        color_map = {
            "info": Colors.BLUE,
            "success": Colors.GREEN,
            "error": Colors.RED,
            "warning": Colors.YELLOW,
        }

        icon_map = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️"}

        color = color_map.get(msg_type, Colors.WHITE)
        icon = icon_map.get(msg_type, "")

        if prefix:
            print(f"{color}{icon} {prefix} {message}{Colors.RESET}")
        else:
            print(f"{color}{icon} {message}{Colors.RESET}")

    def print_info(self, message: str, prefix: str | None = None):
        """打印信息消息"""
        self.print_message(message, "info", prefix)

    def print_success(self, message: str, prefix: str | None = None):
        """打印成功消息"""
        self.print_message(message, "success", prefix)

    def print_error(self, message: str, prefix: str | None = None):
        """打印错误消息"""
        self.print_message(message, "error", prefix)

    def print_warning(self, message: str, prefix: str | None = None):
        """打印警告消息"""
        self.print_message(message, "warning", prefix)

    def format_data(self, data: list[dict] | dict, headers: list[str] | None = None) -> str:
        """
        格式化数据输出

        Args:
            data: 要格式化的数据
            headers: 表格头部（仅在table格式下使用）

        Returns:
            格式化后的字符串
        """
        if self.format_type == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)

        elif self.format_type == "table":
            if not data:
                return "No data available"

            if isinstance(data, dict):
                # 单个对象转换为键值对表格
                table_data = [[k, v] for k, v in data.items()]
                return tabulate(table_data, headers=["Key", "Value"], tablefmt="grid")

            elif isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    # 字典列表转换为表格
                    if not headers:
                        headers = list(data[0].keys())
                    table_data = [[item.get(h, "") for h in headers] for item in data]
                    return tabulate(table_data, headers=headers, tablefmt="grid")
                else:
                    # 简单列表
                    return "\n".join(str(item) for item in data)

        return str(data)

    def print_data(self, data: list[dict] | dict, headers: list[str] | None = None):
        """打印格式化数据"""
        formatted = self.format_data(data, headers)
        print(formatted)

    def print_section(self, title: str, content: str | None = None):
        """打印章节标题"""
        if self.colors:
            print(f"\n{Colors.BOLD}{Colors.CYAN}{title}{Colors.RESET}")
            print("=" * len(title))
        else:
            print(f"\n{title}")
            print("=" * len(title))

        if content:
            print(content)


def format_table(
    data: list[dict[str, Any]],
    headers: list[str] | None = None,
    tablefmt: str = "grid",
) -> str:
    """
    格式化数据为表格

    Args:
        data: 数据列表
        headers: 表头列表
        tablefmt: 表格格式

    Returns:
        格式化的表格字符串
    """
    if not data:
        return "No data available"

    if not headers:
        headers = list(data[0].keys()) if data else []

    table_data = []
    for item in data:
        row = []
        for header in headers:
            value = item.get(header, "")
            # 处理长字符串
            if isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            row.append(value)
        table_data.append(row)

    try:
        return tabulate(table_data, headers=headers, tablefmt=tablefmt)
    except Exception:
        # 如果tabulate不可用，使用简单格式
        result = []
        if headers:
            result.append(" | ".join(headers))
            result.append("-" * len(" | ".join(headers)))

        for row in table_data:
            result.append(" | ".join(str(cell) for cell in row))

        return "\n".join(result)


def print_status(status: str, message: str, colors: bool = True):
    """
    打印状态消息

    Args:
        status: 状态类型 (success, error, warning, info)
        message: 消息内容
        colors: 是否使用颜色
    """
    formatter = OutputFormatter(colors=colors)

    if status == "success":
        formatter.print_success(message)
    elif status == "error":
        formatter.print_error(message)
    elif status == "warning":
        formatter.print_warning(message)
    else:
        formatter.print_info(message)


def format_duration(seconds: float) -> str:
    """格式化持续时间（使用统一的格式化函数）"""
    return _format_duration(seconds)


def format_size(bytes_size: int) -> str:
    """格式化文件大小（使用统一的格式化函数）"""
    return _format_size_compact(bytes_size)


def format_timestamp(timestamp: float | str | datetime) -> str:
    """格式化时间戳（使用统一的格式化函数）"""
    return _format_timestamp(timestamp)


# 向后兼容的全局函数
def print_info(message: str, prefix: str | None = None):
    """打印信息消息"""
    formatter = OutputFormatter()
    formatter.print_info(message, prefix)


def print_success(message: str, prefix: str | None = None):
    """打印成功消息"""
    formatter = OutputFormatter()
    formatter.print_success(message, prefix)


def print_error(message: str, prefix: str | None = None):
    """打印错误消息"""
    formatter = OutputFormatter()
    formatter.print_error(message, prefix)


def print_warning(message: str, prefix: str | None = None):
    """打印警告消息"""
    formatter = OutputFormatter()
    formatter.print_warning(message, prefix)
