# sage/sage_utils/data_loader.py

from pathlib import Path

from pathlib import Path

def resolve_data_path(path: str | Path) -> Path:
    """
    传入相对路径则返回相对于项目根目录的绝对路径（默认假设项目根目录含有 'data/' 子目录），
    传入绝对路径则直接返回。
    """
    import os
    p = Path(path)
    if p.is_absolute():
        return p
    # 假设调用时 cwd 是项目的某个子目录，项目根为“当前工作目录的祖父目录”
    project_root = Path(os.getcwd()).resolve()
    return project_root  / p


def load_data(path: str | Path) -> str:
    file = resolve_data_path(path)
    if not file.is_file():
        raise FileNotFoundError(f"No data file: {file}")
    return file.read_text()
