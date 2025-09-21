#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE Environment Configuration Utilities

This module provides utilities for loading and managing environment variables
for the SAGE project, including API keys and development settings.
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    import pytest

    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


def find_project_root() -> Path:
    """Find the SAGE project root directory."""
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


def load_sage_env(env_file: Optional[str] = None, override: bool = False) -> bool:
    """
    Load environment variables from .env file.

    Args:
        env_file: Path to the .env file. If None, looks for .env in project root.
        override: Whether to override existing environment variables.

    Returns:
        True if .env file was found and loaded, False otherwise.
    """
    if not DOTENV_AVAILABLE:
        print(
            "Warning: python-dotenv not available. Install with: pip install python-dotenv"
        )
        return False

    if env_file is None:
        project_root = find_project_root()
        env_file = project_root / ".env"
    else:
        env_file = Path(env_file)

    if env_file.exists():
        load_dotenv(env_file, override=override)
        print(f"✅ Loaded environment from: {env_file}")
        return True
    else:
        # Look for .env in current directory as fallback
        fallback_env = Path(".env")
        if fallback_env.exists():
            load_dotenv(fallback_env, override=override)
            print(f"✅ Loaded environment from: {fallback_env}")
            return True
        else:
            print(f"ℹ️  No .env file found at {env_file}")
            return False


def should_use_real_api() -> bool:
    """
    Check if we should use real API calls instead of test mode.

    Returns:
        True if should use real API calls, False for test mode
    """
    # Check environment variable first
    if os.getenv("SAGE_USE_REAL_API") == "true":
        return True

    # Check sys.argv for the flag (simple but reliable)
    if "--use-real-api" in sys.argv:
        return True

    return False


def get_api_key(service: str, required: bool = True) -> Optional[str]:
    """
    Get API key for a service with helpful error messages.

    Args:
        service: Service name (e.g., 'openai', 'hf', 'siliconcloud')
        required: Whether the API key is required

    Returns:
        API key string or None

    Raises:
        ValueError: If required API key is missing
    """
    service_mapping = {
        "openai": "OPENAI_API_KEY",
        "hf": "HF_TOKEN",
        "huggingface": "HF_TOKEN",
        "siliconcloud": "SILICONCLOUD_API_KEY",
        "jina": "JINA_API_KEY",
        "alibaba": "ALIBABA_API_KEY",
        "vllm": "VLLM_API_KEY",
    }

    env_var = service_mapping.get(service.lower())
    if not env_var:
        available = ", ".join(service_mapping.keys())
        raise ValueError(f"Unknown service '{service}'. Available: {available}")

    api_key = os.getenv(env_var)

    if not api_key and required:
        project_root = find_project_root()
        raise ValueError(
            f"Missing required API key: {env_var}\n"
            f"Please set it in your .env file at {project_root}/.env\n"
            f"You can copy .env.template to .env and fill in your keys."
        )

    return api_key


def check_environment() -> dict:
    """
    Check the current environment configuration.

    Returns:
        Dictionary with environment status information
    """
    status = {
        "dotenv_available": DOTENV_AVAILABLE,
        "project_root": find_project_root(),
        "env_file_exists": False,
        "env_template_exists": False,
        "api_keys": {},
    }

    project_root = status["project_root"]
    env_file = project_root / ".env"
    env_template = project_root / ".env.template"

    status["env_file_exists"] = env_file.exists()
    status["env_template_exists"] = env_template.exists()

    # Check API keys (but don't show actual values)
    api_keys = [
        "OPENAI_API_KEY",
        "HF_TOKEN",
        "SILICONCLOUD_API_KEY",
        "JINA_API_KEY",
        "ALIBABA_API_KEY",
        "VLLM_API_KEY",
    ]

    for key in api_keys:
        value = os.getenv(key)
        status["api_keys"][key] = {
            "set": value is not None,
            "length": len(value) if value else 0,
        }

    return status


def setup_env_interactive():
    """Interactive setup for environment configuration."""
    print("🔧 SAGE Environment Setup")
    print("=" * 50)

    status = check_environment()
    project_root = status["project_root"]

    print(f"Project root: {project_root}")
    print(f"python-dotenv available: {status['dotenv_available']}")
    print(f".env file exists: {status['env_file_exists']}")
    print(f".env.template exists: {status['env_template_exists']}")

    if not status["env_file_exists"]:
        if status["env_template_exists"]:
            print(f"\n📋 Copy {project_root}/.env.template to {project_root}/.env")
            print("   and fill in your API keys.")
        else:
            print(f"\n📋 Create a .env file at {project_root}/.env")
            print("   with your API keys.")

    print("\n🔑 API Key Status:")
    for key, info in status["api_keys"].items():
        status_icon = "✅" if info["set"] else "❌"
        length_info = f"({info['length']} chars)" if info["set"] else ""
        print(f"  {status_icon} {key} {length_info}")

    return status


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_env_interactive()
    else:
        # Try to load environment
        load_sage_env()
        status = check_environment()

        if not any(info["set"] for info in status["api_keys"].values()):
            print("\n⚠️  No API keys detected!")
            print("Run: python tools/env_config.py setup")
