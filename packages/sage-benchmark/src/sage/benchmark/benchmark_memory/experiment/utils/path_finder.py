from pathlib import Path


def get_project_root() -> Path:
    """
    获取项目根目录（包含 packages 目录的目录）

    Returns:
        Path: 项目根目录路径

    Raises:
        FileNotFoundError: 如果未找到项目根目录
    """
    current_dir = Path.cwd()

    for _ in range(5):
        packages_dir = current_dir / "packages"
        if packages_dir.exists() and packages_dir.is_dir():
            return current_dir

        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent

    raise FileNotFoundError("未找到 SAGE 项目根目录")
