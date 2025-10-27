"""
Utility functions for Examples testing tools

This module provides helper functions for managing the development environment
and locating SAGE examples.
"""

import os
import subprocess
from pathlib import Path


def find_examples_directory() -> Path | None:
    """
    查找 SAGE examples 目录

    这个函数按以下顺序查找：
    1. SAGE_ROOT 环境变量
    2. 从当前工作目录向上查找（开发环境）
    3. Git 仓库根目录

    Returns:
        Path to examples directory if found, None otherwise

    Note:
        这个函数不会抛出异常，如果找不到会返回 None
    """

    # 1. 优先检查环境变量
    if sage_root := os.getenv("SAGE_ROOT"):
        examples = Path(sage_root) / "examples"
        if examples.exists() and examples.is_dir():
            return examples.resolve()

    # 2. 从当前工作目录向上查找（开发环境）
    current = Path.cwd()
    for _ in range(5):  # 最多向上查找5层
        examples = current / "examples"
        # 确认这是 SAGE 项目（通过检查 packages 目录）
        if examples.exists() and (current / "packages").exists():
            return examples.resolve()
        if current.parent == current:  # 到达根目录
            break
        current = current.parent

    # 3. 尝试从脚本位置推断（如果直接运行工具）
    try:
        # 从 sage-tools 包位置向上查找
        tools_path = Path(__file__).resolve()
        # __file__ is in packages/sage-tools/src/sage/tools/dev/examples/utils.py
        # Need to go up 7 levels to reach project root
        potential_root = tools_path.parents[6]
        examples = potential_root / "examples"
        if examples.exists() and (potential_root / "packages").exists():
            return examples.resolve()
    except (IndexError, OSError):
        pass

    # 4. 检查是否在 Git 仓库中
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        git_root = Path(result.stdout.strip())
        examples = git_root / "examples"
        # 确认这是 SAGE 仓库
        if examples.exists() and (git_root / "packages").exists():
            return examples.resolve()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def find_project_root() -> Path | None:
    """
    查找 SAGE 项目根目录

    Returns:
        Path to project root if found, None otherwise
    """
    # 尝试从 sage-common 导入统一的路径管理
    try:
        from sage.common.config.output_paths import find_project_root as find_sage_root

        return find_sage_root()
    except ImportError:
        pass

    # 回退到本地查找逻辑
    examples_dir = find_examples_directory()
    if examples_dir:
        return examples_dir.parent

    return None


def ensure_development_environment(raise_error: bool = False) -> bool:
    """
    确保当前环境是 SAGE 开发环境

    Args:
        raise_error: 如果为 True，在找不到开发环境时抛出异常

    Returns:
        True if development environment is available, False otherwise

    Raises:
        RuntimeError: 如果 raise_error=True 且找不到开发环境
    """
    examples_dir = find_examples_directory()

    if examples_dir is None:
        if raise_error:
            raise RuntimeError(
                "SAGE development environment not found.\n\n"
                "The Examples testing tools require access to the SAGE source code.\n"
                "This is typically only available in a development environment.\n\n"
                "To use these tools:\n"
                "  1. Clone the SAGE repository:\n"
                "     git clone https://github.com/intellistream/SAGE\n"
                "     cd SAGE\n"
                "  2. Install sage-tools from source:\n"
                "     pip install -e packages/sage-tools[dev]\n"
                "  3. Or set the SAGE_ROOT environment variable:\n"
                "     export SAGE_ROOT=/path/to/SAGE\n\n"
                "Note: These tools are designed for SAGE developers and contributors,\n"
                "      not for end users who install via PyPI."
            )
        return False

    return True


def get_development_info() -> dict:
    """
    获取开发环境信息

    Returns:
        Dictionary containing development environment information
    """
    examples_dir = find_examples_directory()
    project_root = find_project_root()

    info = {
        "has_dev_env": examples_dir is not None,
        "examples_dir": str(examples_dir) if examples_dir else None,
        "project_root": str(project_root) if project_root else None,
        "sage_root_env": os.getenv("SAGE_ROOT"),
        "in_git_repo": False,
    }

    # 检查是否在 Git 仓库中
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True, check=True, timeout=2
        )
        info["in_git_repo"] = True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return info
