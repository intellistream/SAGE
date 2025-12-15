from pathlib import Path


def get_project_root() -> Path:
    """
    获取项目根目录（包含 packages 目录的目录）

    Returns:
        Path: 项目根目录路径

    Raises:
        FileNotFoundError: 如果未找到项目根目录
    """
    # Use centralized project root finding function from sage-common
    from sage.common.config import find_sage_project_root

    project_root = find_sage_project_root()
    if project_root is None:
        raise FileNotFoundError("未找到 SAGE 项目根目录")
    return project_root
