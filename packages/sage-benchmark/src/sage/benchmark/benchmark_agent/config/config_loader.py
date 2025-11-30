"""
Configuration Loader for Agent Benchmark Experiments

Provides utilities for loading and parsing YAML configuration files
with environment variable substitution.
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml

from sage.benchmark.benchmark_agent.experiments.base_experiment import (
    ExperimentConfig,
    create_config,
)


class ConfigLoader:
    """
    Loader for experiment YAML configurations.

    Supports:
    - Environment variable substitution (${VAR} or $VAR)
    - Special ${PROJECT_ROOT} variable
    - Type-safe config object creation
    """

    @staticmethod
    def _find_project_root() -> Path:
        """Find project root directory (where .git exists)."""
        current = Path.cwd()
        while current.parent != current:
            if (current / ".git").exists():
                return current
            current = current.parent
        return Path.cwd()

    @staticmethod
    def _expand_vars(value: Any, context: Optional[dict[str, str]] = None) -> Any:
        """
        Recursively expand environment variables in config values.

        Args:
            value: Config value (can be str, dict, list, etc.)
            context: Additional variable context

        Returns:
            Value with expanded variables
        """
        if context is None:
            context = {}

        # Add PROJECT_ROOT to context
        if "PROJECT_ROOT" not in context:
            context["PROJECT_ROOT"] = str(ConfigLoader._find_project_root())

        if isinstance(value, str):
            # Pattern matches ${VAR} or $VAR
            pattern = r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)"

            def replacer(match):
                var_name = match.group(1) or match.group(2)
                # Check context first, then environment
                return context.get(var_name, os.environ.get(var_name, match.group(0)))

            return re.sub(pattern, replacer, value)

        elif isinstance(value, dict):
            return {k: ConfigLoader._expand_vars(v, context) for k, v in value.items()}

        elif isinstance(value, list):
            return [ConfigLoader._expand_vars(item, context) for item in value]

        return value

    @classmethod
    def load_yaml(cls, config_path) -> dict[str, Any]:
        """
        Load and parse YAML config file.

        Args:
            config_path: Path to YAML config file (str or Path)

        Returns:
            Parsed config dictionary with expanded variables
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        # Expand environment variables
        expanded = cls._expand_vars(raw_config)

        return expanded

    @classmethod
    def load_config(cls, config_path) -> ExperimentConfig:
        """
        Load YAML config and create typed config object.

        Args:
            config_path: Path to YAML config file (str or Path)

        Returns:
            ExperimentConfig subclass instance
        """
        config_dict = cls.load_yaml(config_path)
        return create_config(config_dict)

    @classmethod
    def load_default_config(cls) -> dict[str, Any]:
        """
        Load default configuration.

        Returns:
            Default config dictionary
        """
        default_path = Path(__file__).parent.parent / "config" / "default_config.yaml"
        if default_path.exists():
            return cls.load_yaml(default_path)
        return {}

    @classmethod
    def merge_configs(
        cls, base_config: dict[str, Any], override_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge two configuration dictionaries.

        Args:
            base_config: Base configuration
            override_config: Override configuration

        Returns:
            Merged configuration (override takes precedence)
        """
        merged = base_config.copy()

        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = cls.merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged


def load_config_with_defaults(config_path: Path) -> ExperimentConfig:
    """
    Load config with default values merged in.

    Args:
        config_path: Path to experiment config file

    Returns:
        ExperimentConfig with defaults applied
    """
    loader = ConfigLoader()

    # Load default config
    defaults = loader.load_default_config()

    # Load experiment config
    exp_config = loader.load_yaml(config_path)

    # Merge
    merged = loader.merge_configs(defaults, exp_config)

    # Create typed config
    return create_config(merged)
