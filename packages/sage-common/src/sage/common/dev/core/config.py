"""
Configuration management for SAGE Development Toolkit.

This module handles loading, validating, and managing configuration
for the development toolkit, supporting multiple environments and
configuration sources.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

from .exceptions import ConfigError


@dataclass
class ToolkitConfig:
    """Configuration container for SAGE Development Toolkit."""
    
    # Project paths
    project_root: Path
    packages_dir: Path
    scripts_dir: Path
    output_dir: Path  
    logs_dir: Path
    temp_dir: Path
    
    # Configuration data
    config_data: Dict[str, Any] = field(default_factory=dict)
    
    # Environment
    environment: str = "development"
    
    @classmethod
    def from_config_file(
        cls, 
        config_path: Optional[Path] = None, 
        project_root: Optional[Path] = None,
        environment: Optional[str] = None
    ) -> "ToolkitConfig":
        """
        Create configuration from file.
        
        Args:
            config_path: Path to configuration file
            project_root: Project root directory
            environment: Environment name (development, production, ci)
            
        Returns:
            ToolkitConfig instance
            
        Raises:
            ConfigError: If configuration cannot be loaded or is invalid
        """
        if project_root is None:
            project_root = Path.cwd()
        else:
            project_root = Path(project_root)
            
        if config_path is None:
            # Try multiple default locations
            for candidate in [
                project_root / "sage_common.yaml",
                project_root / "dev-toolkit" / "config" / "default.yaml",
                project_root / ".sage-dev-config.yaml"
            ]:
                if candidate.exists():
                    config_path = candidate
                    break
            else:
                # Use default configuration if no file found
                config_path = None
        
        # Load configuration data
        config_data = {}
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                raise ConfigError(
                    f"Failed to load configuration from {config_path}",
                    config_path=str(config_path),
                    cause=e
                )
        
        # Determine environment
        if environment is None:
            environment = os.getenv('SAGE_DEV_ENV', config_data.get('environment', 'development'))
        
        # Apply environment-specific overrides
        env_config = config_data.get('environments', {}).get(environment, {})
        config_data = cls._merge_configs(config_data, env_config)
        
        # Extract directory configuration
        dirs = config_data.get('directories', {})
        
        # Set up paths using ~/.sage/ directory structure
        sage_home = Path.home() / ".sage"
        project_name = project_root.name
        
        # Use direct ~/.sage path for SAGE project, projects subdirectory for others
        if project_name and project_name.upper() == "SAGE":
            project_sage_dir = sage_home
        else:
            project_sage_dir = sage_home / "projects" / project_name
        
        return cls(
            project_root=project_root,
            packages_dir=project_root / dirs.get('packages', 'packages'),
            scripts_dir=project_root / dirs.get('scripts', 'scripts'),
            output_dir=project_sage_dir / "reports",  # Use ~/.sage/ for outputs
            logs_dir=project_sage_dir / "logs",       # Use ~/.sage/ for logs  
            temp_dir=project_sage_dir / "temp",       # Use ~/.sage/ for temp files
            config_data=config_data,
            environment=environment
        )
    
    @staticmethod
    def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ToolkitConfig._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key path."""
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def get_testing_config(self) -> Dict[str, Any]:
        """Get testing-specific configuration."""
        return self.get('testing', {})
    
    def get_dependency_config(self) -> Dict[str, Any]:
        """Get dependency analysis configuration."""
        return self.get('dependency_analysis', {})
    
    def get_package_config(self) -> Dict[str, Any]:
        """Get package management configuration."""  
        return self.get('package_management', {})
    
    def get_reporting_config(self) -> Dict[str, Any]:
        """Get reporting configuration."""
        return self.get('reporting', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get('logging', {})
    
    def get_tools_config(self) -> Dict[str, Any]:
        """Get tools configuration."""
        return self.get('tools', {})
    
    def get_interactive_config(self) -> Dict[str, Any]:
        """Get interactive mode configuration."""
        return self.get('interactive', {})
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled."""
        tools_config = self.get_tools_config()
        tool_config = tools_config.get(tool_name, {})
        return tool_config.get('enabled', True)
    
    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific tool."""
        tools_config = self.get_tools_config()
        return tools_config.get(tool_name, {})
    
    def ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        directories = [
            self.output_dir,
            self.logs_dir,
            self.temp_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of validation errors.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check required directories exist
        if not self.project_root.exists():
            errors.append(f"Project root does not exist: {self.project_root}")
        
        if not self.packages_dir.exists():
            errors.append(f"Packages directory does not exist: {self.packages_dir}")
            
        if not self.scripts_dir.exists():
            errors.append(f"Scripts directory does not exist: {self.scripts_dir}")
        
        # Validate tools configuration
        tools_config = self.get_tools_config()
        for tool_name, tool_config in tools_config.items():
            if not isinstance(tool_config, dict):
                errors.append(f"Tool configuration for '{tool_name}' must be a dictionary")
                continue
                
            if 'module' not in tool_config:
                errors.append(f"Tool '{tool_name}' missing required 'module' configuration")
                
            if 'class' not in tool_config:
                errors.append(f"Tool '{tool_name}' missing required 'class' configuration")
        
        return errors
    
    def __str__(self) -> str:
        return f"ToolkitConfig(environment={self.environment}, project_root={self.project_root})"
    
    def __repr__(self) -> str:
        return (
            f"ToolkitConfig("
            f"project_root={self.project_root!r}, "
            f"environment={self.environment!r}, "
            f"packages_dir={self.packages_dir!r}, "
            f"scripts_dir={self.scripts_dir!r}"
            f")"
        )
