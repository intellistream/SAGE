"""SAGE User Path Configuration (XDG Base Directory Specification)

Layer: L1 (Foundation - Common Configuration)

This module provides XDG-compliant user directory paths for SAGE.
Following the XDG Base Directory Specification:
- https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

Path Categories:
- CONFIG: User configuration files (edited by user, should be backed up)
- DATA: Persistent application data (sessions, databases, models)
- STATE: Runtime state data (logs, history)
- CACHE: Non-essential cached data (can be deleted to free space)

Directory Structure:
    $XDG_CONFIG_HOME/sage/     (~/.config/sage/)
    ├── config.yaml            # Main configuration
    ├── cluster.yaml           # Cluster configuration
    └── credentials.yaml       # API keys (should be 600 permission)

    $XDG_DATA_HOME/sage/       (~/.local/share/sage/)
    ├── models/                # Downloaded models
    │   └── vllm/
    ├── sessions/              # Gateway sessions
    ├── vector_db/             # Vector database indices
    └── finetune/              # Fine-tuning outputs

    $XDG_STATE_HOME/sage/      (~/.local/state/sage/)
    └── logs/                  # Runtime logs
        ├── gateway.log
        ├── llm_server.log
        └── studio.log

    $XDG_CACHE_HOME/sage/      (~/.cache/sage/)
    ├── huggingface/           # HuggingFace cache
    ├── pip/                   # Pip cache
    └── chat/                  # Chat index cache

Note: Project-level temporary files (.sage/) are managed by output_paths.py
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

# Type alias for path categories
PathCategory = Literal["config", "data", "state", "cache"]


def _get_xdg_dir(env_var: str, default_subdir: str) -> Path:
    """Get XDG directory with fallback to default.

    Args:
        env_var: Environment variable name (e.g., "XDG_CONFIG_HOME")
        default_subdir: Default subdirectory under $HOME (e.g., ".config")

    Returns:
        Path to the XDG directory
    """
    xdg_dir = os.environ.get(env_var)
    if xdg_dir:
        return Path(xdg_dir)
    return Path.home() / default_subdir


@lru_cache(maxsize=1)
def get_user_config_dir() -> Path:
    """Get SAGE user configuration directory.

    Default: ~/.config/sage/

    This directory contains user-editable configuration files.
    Should be backed up.

    Returns:
        Path to config directory
    """
    base = _get_xdg_dir("XDG_CONFIG_HOME", ".config")
    sage_dir = base / "sage"
    sage_dir.mkdir(parents=True, exist_ok=True)
    return sage_dir


@lru_cache(maxsize=1)
def get_user_data_dir() -> Path:
    """Get SAGE user data directory.

    Default: ~/.local/share/sage/

    This directory contains persistent application data:
    - Downloaded models
    - Session data
    - Vector databases
    - Fine-tuning outputs

    Returns:
        Path to data directory
    """
    base = _get_xdg_dir("XDG_DATA_HOME", ".local/share")
    sage_dir = base / "sage"
    sage_dir.mkdir(parents=True, exist_ok=True)
    return sage_dir


@lru_cache(maxsize=1)
def get_user_state_dir() -> Path:
    """Get SAGE user state directory.

    Default: ~/.local/state/sage/

    This directory contains runtime state data:
    - Log files
    - History files
    - PID files

    Returns:
        Path to state directory
    """
    base = _get_xdg_dir("XDG_STATE_HOME", ".local/state")
    sage_dir = base / "sage"
    sage_dir.mkdir(parents=True, exist_ok=True)
    return sage_dir


@lru_cache(maxsize=1)
def get_user_cache_dir() -> Path:
    """Get SAGE user cache directory.

    Default: ~/.cache/sage/

    This directory contains non-essential cached data.
    Can be safely deleted to free disk space.

    Returns:
        Path to cache directory
    """
    base = _get_xdg_dir("XDG_CACHE_HOME", ".cache")
    sage_dir = base / "sage"
    sage_dir.mkdir(parents=True, exist_ok=True)
    return sage_dir


class SageUserPaths:
    """Centralized access to SAGE user directories following XDG specification.

    Usage:
        from sage.common.config.user_paths import SageUserPaths

        paths = SageUserPaths()
        config_file = paths.config_dir / "config.yaml"
        log_file = paths.logs_dir / "gateway.log"
        model_dir = paths.models_dir / "vllm"
    """

    def __init__(self):
        """Initialize user paths and ensure directory structure exists."""
        self._ensure_structure()

    def _ensure_structure(self):
        """Ensure all required subdirectories exist."""
        # Config subdirectories (none needed, flat structure)

        # Data subdirectories
        for subdir in ["models", "models/vllm", "sessions", "vector_db", "finetune"]:
            (self.data_dir / subdir).mkdir(parents=True, exist_ok=True)

        # State subdirectories
        for subdir in ["logs"]:
            (self.state_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Cache subdirectories
        for subdir in ["huggingface", "chat"]:
            (self.cache_dir / subdir).mkdir(parents=True, exist_ok=True)

    # === Base directories ===

    @property
    def config_dir(self) -> Path:
        """User configuration directory (~/.config/sage/)"""
        return get_user_config_dir()

    @property
    def data_dir(self) -> Path:
        """User data directory (~/.local/share/sage/)"""
        return get_user_data_dir()

    @property
    def state_dir(self) -> Path:
        """User state directory (~/.local/state/sage/)"""
        return get_user_state_dir()

    @property
    def cache_dir(self) -> Path:
        """User cache directory (~/.cache/sage/)"""
        return get_user_cache_dir()

    # === Config paths ===

    @property
    def config_file(self) -> Path:
        """Main configuration file (~/.config/sage/config.yaml)"""
        return self.config_dir / "config.yaml"

    @property
    def cluster_config_file(self) -> Path:
        """Cluster configuration file (~/.config/sage/cluster.yaml)"""
        return self.config_dir / "cluster.yaml"

    @property
    def credentials_file(self) -> Path:
        """Credentials file (~/.config/sage/credentials.yaml)"""
        return self.config_dir / "credentials.yaml"

    # === Data paths ===

    @property
    def models_dir(self) -> Path:
        """Downloaded models directory (~/.local/share/sage/models/)"""
        return self.data_dir / "models"

    @property
    def vllm_models_dir(self) -> Path:
        """vLLM models directory (~/.local/share/sage/models/vllm/)"""
        return self.data_dir / "models" / "vllm"

    @property
    def sessions_dir(self) -> Path:
        """Session data directory (~/.local/share/sage/sessions/)"""
        return self.data_dir / "sessions"

    @property
    def vector_db_dir(self) -> Path:
        """Vector database directory (~/.local/share/sage/vector_db/)"""
        return self.data_dir / "vector_db"

    @property
    def finetune_dir(self) -> Path:
        """Fine-tuning output directory (~/.local/share/sage/finetune/)"""
        return self.data_dir / "finetune"

    # === State paths ===

    @property
    def logs_dir(self) -> Path:
        """Log files directory (~/.local/state/sage/logs/)"""
        return self.state_dir / "logs"

    def get_log_file(self, name: str) -> Path:
        """Get path to a specific log file.

        Args:
            name: Log file name (e.g., "gateway", "llm_server", "studio")

        Returns:
            Path to log file
        """
        if not name.endswith(".log"):
            name = f"{name}.log"
        return self.logs_dir / name

    # === Cache paths ===

    @property
    def hf_cache_dir(self) -> Path:
        """HuggingFace cache directory (~/.cache/sage/huggingface/)"""
        return self.cache_dir / "huggingface"

    @property
    def chat_cache_dir(self) -> Path:
        """Chat index cache directory (~/.cache/sage/chat/)"""
        return self.cache_dir / "chat"


# Singleton instance for convenience
_user_paths: SageUserPaths | None = None


def get_user_paths() -> SageUserPaths:
    """Get singleton instance of SageUserPaths.

    Usage:
        from sage.common.config.user_paths import get_user_paths

        paths = get_user_paths()
        config = paths.config_file
    """
    global _user_paths
    if _user_paths is None:
        _user_paths = SageUserPaths()
    return _user_paths


# === Legacy compatibility ===
# These functions provide backward compatibility with code using ~/.sage/


def get_legacy_sage_home() -> Path:
    """Get legacy ~/.sage/ path for backward compatibility.

    DEPRECATED: Use get_user_paths() instead.

    This function is provided for migration purposes only.
    New code should use the XDG-compliant paths.

    Returns:
        Path to ~/.sage/
    """
    sage_home = Path.home() / ".sage"
    sage_home.mkdir(parents=True, exist_ok=True)
    return sage_home


def migrate_legacy_config():
    """Migrate configuration from legacy ~/.sage/ to XDG paths.

    This function checks for legacy configuration files and migrates
    them to the new XDG-compliant locations.
    """
    import shutil

    legacy_home = Path.home() / ".sage"
    paths = get_user_paths()

    # Migration mappings: (legacy_path, new_path)
    migrations = [
        (legacy_home / "config.yaml", paths.config_file),
        (legacy_home / "cluster_config.yaml", paths.cluster_config_file),
        (legacy_home / ".env.json", paths.config_dir / "env.json"),
    ]

    for legacy_path, new_path in migrations:
        if legacy_path.exists() and not new_path.exists():
            print(f"Migrating {legacy_path} -> {new_path}")
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_path, new_path)


# Export all public symbols
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
