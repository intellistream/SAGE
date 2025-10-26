"""Environment configuration utilities for the SAGE toolchain."""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:  # pragma: no cover - import fallback is runtime dependent
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - handled at runtime
    load_dotenv = None  # type: ignore


def find_project_root(start: Path | None = None) -> Path:
    """Locate the SAGE project root directory.

    The lookup walks upwards from ``start`` (or the current file location when
    omitted) until a directory containing either ``pyproject.toml`` or ``.git``
    is found. If no sentinel is discovered the current working directory is
    returned.
    """

    current = start or Path(__file__).resolve().parent
    pyproject_candidate: Path | None = None

    while current != current.parent:
        if (current / ".git").exists():
            return current
        if pyproject_candidate is None and (current / "pyproject.toml").exists():
            pyproject_candidate = current
        current = current.parent

    if pyproject_candidate is not None:
        return pyproject_candidate
    return Path.cwd()


def load_environment_file(
    env_file: Path | None = None, *, override: bool = False
) -> tuple[bool, Path | None]:
    """Load a ``.env`` file into the current process.

    Args:
        env_file: Optional explicit path to the ``.env`` file. When omitted the
            helper searches ``find_project_root() / ".env"`` first and falls
            back to ``Path.cwd() / ".env"``.
        override: When ``True`` existing environment variables are replaced by
            the values from the file.

    Returns:
        A tuple ``(loaded, path)`` where ``loaded`` indicates whether a file was
        successfully consumed and ``path`` references the resolved file that was
        used. If no file could be loaded ``path`` is ``None``.

    Raises:
        RuntimeError: If the optional dependency ``python-dotenv`` is missing.
    """

    if load_dotenv is None:
        raise RuntimeError(
            "python-dotenv is not installed. Install it with 'pip install python-dotenv'."
        )

    candidate: Path | None = None
    if env_file is not None:
        candidate = env_file.expanduser()
    else:
        project_env = find_project_root() / ".env"
        if project_env.exists():
            candidate = project_env
        else:
            local_env = Path.cwd() / ".env"
            if local_env.exists():
                candidate = local_env

    if candidate is None or not candidate.exists():
        return False, candidate

    load_dotenv(candidate, override=override)
    return True, candidate


def should_use_real_api() -> bool:
    """Return ``True`` when real API calls should be executed."""

    if os.getenv("SAGE_USE_REAL_API") == "true":
        return True
    return "--use-real-api" in sys.argv


def get_api_key(service: str, *, required: bool = True) -> str | None:
    """Fetch the API key for *service* from the environment.

    Args:
        service: Logical service identifier (``openai``, ``hf`` …).
        required: When ``True`` a ``ValueError`` is raised if the key is
            missing. Otherwise ``None`` is returned.
    """

    mapping = {
        "openai": "OPENAI_API_KEY",
        "hf": "HF_TOKEN",
        "huggingface": "HF_TOKEN",
        "siliconcloud": "SILICONCLOUD_API_KEY",
        "jina": "JINA_API_KEY",
        "alibaba": "ALIBABA_API_KEY",
        "vllm": "VLLM_API_KEY",
    }

    env_var = mapping.get(service.lower())
    if not env_var:
        available = ", ".join(sorted(mapping))
        raise ValueError(f"Unknown service '{service}'. Available services: {available}")

    value = os.getenv(env_var)
    if not value and required:
        project_root = find_project_root()
        raise ValueError(
            f"Missing required API key: {env_var}. "
            f"Set it in your .env file (see {project_root}/.env or .env.template)."
        )

    return value


def check_environment_status() -> dict[str, object]:
    """Collect high-level information about the current environment state."""

    project_root = find_project_root()
    env_file = project_root / ".env"
    env_template = project_root / ".env.template"

    api_keys = [
        "OPENAI_API_KEY",
        "HF_TOKEN",
        "SILICONCLOUD_API_KEY",
        "JINA_API_KEY",
        "ALIBABA_API_KEY",
        "VLLM_API_KEY",
    ]

    return {
        "dotenv_available": load_dotenv is not None,
        "project_root": project_root,
        "env_file_exists": env_file.exists(),
        "env_template_exists": env_template.exists(),
        "env_file": env_file,
        "env_template": env_template,
        "api_keys": {
            key: {
                "set": os.getenv(key) is not None,
                "length": len(os.getenv(key) or ""),
            }
            for key in api_keys
        },
    }


__all__ = [
    "check_environment_status",
    "find_project_root",
    "get_api_key",
    "load_environment_file",
    "should_use_real_api",
]
