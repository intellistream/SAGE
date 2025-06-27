# sage/utils/data_loader.py

from pathlib import Path

def resolve_data_path(path: str | Path) -> Path:
    import os
    root = Path(os.getcwd()).resolve().parents[1]

    p = Path(path)
    return p if p.is_absolute() else root / "data" / p

def load_data(path: str | Path) -> str:
    file = resolve_data_path(path)
    if not file.is_file():
        raise FileNotFoundError(f"No data file: {file}")
    return file.read_text()
