#!/usr/bin/env python3
"""
Project Utilities
=================

项目相关的工具函数
"""

from pathlib import Path


def find_project_root(
    start_path: Path | None = None, markers: list[str] | None = None
) -> Path | None:
    """
    查找项目根目录

    Args:
        start_path: 开始查找的路径，默认为当前目录
        markers: 用于识别项目根目录的标记文件/目录

    Returns:
        项目根目录路径，如果找不到返回None
    """
    if start_path is None:
        start_path = Path.cwd()

    if markers is None:
        markers = [
            "setup.py",
            "pyproject.toml",
            "requirements.txt",
            ".git",
            "sage",
            "packages",
            "SAGE_API_REFACTOR_SUMMARY.md",
        ]

    current = Path(start_path).resolve()

    # 向上查找包含标记文件的路径
    for parent in [current] + list(current.parents):
        if any((parent / marker).exists() for marker in markers):
            return parent

    # 检查当前Python环境中的sage包位置
    try:
        import sage

        sage_path = Path(sage.__file__).parent.parent
        if any((sage_path / marker).exists() for marker in markers):
            return sage_path
    except ImportError:
        pass

    return None
