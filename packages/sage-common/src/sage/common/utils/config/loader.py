# sage/sage.common.utils/config_loader.py

import inspect
import os
from pathlib import Path

import yaml
from platformdirs import site_config_dir, user_config_dir


def load_config(path: str | Path | None = None) -> dict:
    # locate project root (…/SAGE/)
    # root = Path(__file__).resolve().parents[2]
    # 获取调用者的文件路径作为项目根目录的参考点
    caller_frame = inspect.currentframe()
    if caller_frame and caller_frame.f_back:
        caller_file = caller_frame.f_back.f_globals.get("__file__")
        if caller_file:
            # 假设调用者在项目根目录或其子目录中
            root = Path(caller_file).resolve().parent
            # 向上查找直到找到包含常见项目标识的目录（最多向上10层）
            max_depth = 10
            depth = 0
            while root.parent != root and depth < max_depth:
                if any(
                    (root / marker).exists()
                    for marker in ["setup.py", "pyproject.toml", ".git", "config"]
                ):
                    break
                root = root.parent
                depth += 1
        else:
            # 回退到当前工作目录
            root = Path.cwd()
    else:
        # 回退到当前工作目录
        root = Path.cwd()
    candidates = []

    # 1. explicit path
    if path:
        raw = Path(path)
        if raw.is_absolute():
            p = raw
        elif not raw.parent.parts:  # bare filename
            p = root / "config" / raw
        else:  # e.g. "config/foo.yaml"
            p = root / raw
        candidates.append(p)

    # 2. env var override
    env = os.getenv("SAGE_CONFIG")
    if env:
        raw = Path(env)
        p = raw if raw.is_absolute() else root / raw
        candidates.append(p)

    # 3. project-level default
    candidates.append(root / "config" / "config.yaml")

    # 4. user-level
    candidates.append(Path(user_config_dir("sage")) / "config.yaml")

    # 5. system-level
    candidates.append(Path(site_config_dir("sage")) / "config.yaml")

    for cfg_path in candidates:
        if cfg_path.is_file():
            return yaml.safe_load(cfg_path.read_text())

    names = "\n".join(str(p) for p in candidates)
    raise FileNotFoundError(f"No config found. Checked:\n{names}")
