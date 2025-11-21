"""
Configuration management for DyFlow.

Provides YAML-based configuration loading and management following SAGE standards.

Layer: L3 (Core Library)
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """
    Load DyFlow configuration from YAML file.

    Args:
        config_path: Path to configuration file. If None, loads default.yaml

    Returns:
        Dictionary containing configuration values

    Example:
        >>> config = load_config()
        >>> designer_model = config['model_service']['designer_model']
    """
    if config_path is None:
        # Load default config from this directory
        config_dir = Path(__file__).parent
        config_path = config_dir / "default.yaml"

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Expand environment variables in API keys
    if "api_keys" in config:
        for key, value in config["api_keys"].items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config["api_keys"][key] = os.getenv(env_var)

    return config


def get_model_config(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Get model service configuration.

    Args:
        config: Full configuration dictionary. If None, loads default.

    Returns:
        Model service configuration
    """
    if config is None:
        config = load_config()

    return config.get("model_service", {})


def get_workflow_config(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Get workflow executor configuration.

    Args:
        config: Full configuration dictionary. If None, loads default.

    Returns:
        Workflow configuration
    """
    if config is None:
        config = load_config()

    return config.get("workflow", {})


def get_operator_config(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Get operator configuration.

    Args:
        config: Full configuration dictionary. If None, loads default.

    Returns:
        Operator configuration
    """
    if config is None:
        config = load_config()

    return config.get("operator", {})


__all__ = [
    "load_config",
    "get_model_config",
    "get_workflow_config",
    "get_operator_config",
]
