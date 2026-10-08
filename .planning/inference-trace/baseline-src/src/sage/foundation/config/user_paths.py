"""XDG-compliant user paths for the in-tree SAGE foundation layer."""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Literal

PathCategory = Literal["config", "data", "state", "cache"]


def _get_xdg_dir(env_var: str, default_subdir: str) -> Path:
    xdg_dir = os.environ.get(env_var)
    if xdg_dir:
        return Path(xdg_dir)
    return Path.home() / default_subdir


@lru_cache(maxsize=1)
def get_user_config_dir() -> Path:
    base = _get_xdg_dir("XDG_CONFIG_HOME", ".config")
    path = base / "sage"
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=1)
def get_user_data_dir() -> Path:
    base = _get_xdg_dir("XDG_DATA_HOME", ".local/share")
    path = base / "sage"
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=1)
def get_user_state_dir() -> Path:
    base = _get_xdg_dir("XDG_STATE_HOME", ".local/state")
    path = base / "sage"
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=1)
def get_user_cache_dir() -> Path:
    base = _get_xdg_dir("XDG_CACHE_HOME", ".cache")
    path = base / "sage"
    path.mkdir(parents=True, exist_ok=True)
    return path


class SageUserPaths:
    """Centralized XDG-style paths for config, data, state, and cache."""

    def __init__(self) -> None:
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        for subdir in [
            "models",
            "models/sagellm",
            "sessions",
            "vector_db",
            "finetune",
            "flows",
        ]:
            (self.data_dir / subdir).mkdir(parents=True, exist_ok=True)

        for subdir in ["logs"]:
            (self.state_dir / subdir).mkdir(parents=True, exist_ok=True)

        for subdir in ["huggingface", "sagellm", "stream"]:
            (self.cache_dir / subdir).mkdir(parents=True, exist_ok=True)

    @property
    def config_dir(self) -> Path:
        return get_user_config_dir()

    @property
    def data_dir(self) -> Path:
        return get_user_data_dir()

    @property
    def state_dir(self) -> Path:
        return get_user_state_dir()

    @property
    def cache_dir(self) -> Path:
        return get_user_cache_dir()

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.yaml"

    @property
    def cluster_config_file(self) -> Path:
        return self.config_dir / "cluster.yaml"

    @property
    def credentials_file(self) -> Path:
        return self.config_dir / "credentials.yaml"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def sagellm_models_dir(self) -> Path:
        return self.models_dir / "sagellm"

    @property
    def sessions_dir(self) -> Path:
        return self.data_dir / "sessions"

    @property
    def vector_db_dir(self) -> Path:
        return self.data_dir / "vector_db"

    @property
    def finetune_dir(self) -> Path:
        return self.data_dir / "finetune"

    @property
    def flows_dir(self) -> Path:
        return self.data_dir / "flows"

    @property
    def logs_dir(self) -> Path:
        return self.state_dir / "logs"

    def get_log_file(self, name: str) -> Path:
        if not name.endswith(".log"):
            name = f"{name}.log"
        return self.logs_dir / name

    @property
    def hf_cache_dir(self) -> Path:
        return self.cache_dir / "huggingface"

    @property
    def stream_cache_dir(self) -> Path:
        return self.cache_dir / "stream"

    @property
    def sagellm_cache_dir(self) -> Path:
        return self.cache_dir / "sagellm"


_user_paths: SageUserPaths | None = None


def get_user_paths() -> SageUserPaths:
    global _user_paths
    if _user_paths is None:
        _user_paths = SageUserPaths()
    return _user_paths


def get_legacy_sage_home() -> Path:
    """Return legacy ``~/.sage`` path for migration only."""
    path = Path.home() / ".sage"
    path.mkdir(parents=True, exist_ok=True)
    return path


def migrate_legacy_config() -> None:
    """Migrate a small set of legacy config files into XDG locations."""
    legacy_home = Path.home() / ".sage"
    paths = get_user_paths()

    migrations = [
        (legacy_home / "config.yaml", paths.config_file),
        (legacy_home / "cluster_config.yaml", paths.cluster_config_file),
        (legacy_home / ".env.json", paths.config_dir / "env.json"),
    ]

    for legacy_path, new_path in migrations:
        if legacy_path.exists() and not new_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_path, new_path)


__all__ = [
    "PathCategory",
    "get_user_config_dir",
    "get_user_data_dir",
    "get_user_state_dir",
    "get_user_cache_dir",
    "SageUserPaths",
    "get_user_paths",
    "get_legacy_sage_home",
    "migrate_legacy_config",
]
