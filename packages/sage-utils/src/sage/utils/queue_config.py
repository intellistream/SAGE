"""
Queue Configuration Management

Handles configuration settings for different queue backends and provides
unified configuration interface.
"""

import os
import yaml
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field


@dataclass
class QueueConfig:
    """Configuration for queue systems."""
    
    # Backend selection
    backend: str = "auto"  # auto, sage_queue, ray_queue, python_queue
    
    # Common queue settings
    maxsize: int = 1024 * 1024  # Default queue size
    auto_cleanup: bool = True
    timeout: float = 30.0
    
    # SAGE queue specific settings
    namespace: Optional[str] = None
    enable_multi_tenant: bool = True
    mmap_path: Optional[str] = None
    
    # Ray queue specific settings
    ray_address: Optional[str] = None
    actor_options: Dict[str, Any] = field(default_factory=dict)
    
    # Performance settings
    batch_size: int = 1
    prefetch_count: int = 0
    enable_compression: bool = False
    
    # Monitoring and logging
    enable_metrics: bool = False
    log_level: str = "INFO"
    stats_interval: int = 60
    
    # Fallback settings
    fallback_backend: str = "python_queue"
    auto_fallback: bool = True


class QueueConfigManager:
    """Manages queue configuration loading and validation."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config: Optional[QueueConfig] = None
        
    def load_config(self, config_data: Optional[Union[str, Dict[str, Any]]] = None) -> QueueConfig:
        """
        Load configuration from file, dict, or use defaults.
        
        Args:
            config_data: Configuration file path, dict, or None for defaults
            
        Returns:
            QueueConfig instance
        """
        if config_data is None:
            # Use defaults with environment variable overrides
            config_dict = self._get_env_overrides()
        elif isinstance(config_data, str):
            # Load from file
            config_dict = self._load_from_file(config_data)
        elif isinstance(config_data, dict):
            # Use provided dict
            config_dict = config_data
        else:
            raise ValueError("config_data must be str (path), dict, or None")
        
        # Apply environment overrides
        config_dict.update(self._get_env_overrides())
        
        self._config = QueueConfig(**config_dict)
        return self._config
    
    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                return yaml.safe_load(f) or {}
            elif file_path.endswith('.json'):
                import json
                return json.load(f)
            else:
                raise ValueError("Config file must be .yaml, .yml, or .json")
    
    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        overrides = {}
        
        # Map environment variables to config fields
        env_mapping = {
            'SAGE_QUEUE_BACKEND': 'backend',
            'SAGE_QUEUE_MAXSIZE': ('maxsize', int),
            'SAGE_QUEUE_TIMEOUT': ('timeout', float),
            'SAGE_QUEUE_NAMESPACE': 'namespace',
            'SAGE_QUEUE_MMAP_PATH': 'mmap_path',
            'SAGE_QUEUE_AUTO_CLEANUP': ('auto_cleanup', bool),
            'SAGE_QUEUE_ENABLE_MULTI_TENANT': ('enable_multi_tenant', bool),
            'SAGE_QUEUE_LOG_LEVEL': 'log_level',
            'SAGE_QUEUE_ENABLE_METRICS': ('enable_metrics', bool),
            'RAY_ADDRESS': 'ray_address'
        }
        
        for env_var, config_field in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if isinstance(config_field, tuple):
                    field_name, field_type = config_field
                    if field_type == bool:
                        overrides[field_name] = env_value.lower() in ('true', '1', 'yes')
                    else:
                        overrides[field_name] = field_type(env_value)
                else:
                    overrides[config_field] = env_value
        
        return overrides
    
    def get_config(self) -> QueueConfig:
        """Get current configuration, loading defaults if not loaded."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def validate_config(self, config: QueueConfig) -> bool:
        """Validate configuration settings."""
        try:
            # Check backend validity
            valid_backends = ['auto', 'sage_queue', 'ray_queue', 'python_queue']
            if config.backend not in valid_backends:
                raise ValueError(f"Invalid backend: {config.backend}")
            
            # Check size limits
            if config.maxsize <= 0:
                raise ValueError("maxsize must be positive")
            
            if config.timeout <= 0:
                raise ValueError("timeout must be positive")
            
            # Check paths
            if config.mmap_path and not os.path.isdir(os.path.dirname(config.mmap_path)):
                raise ValueError(f"Invalid mmap_path directory: {config.mmap_path}")
            
            return True
            
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def save_config(self, config: QueueConfig, file_path: str):
        """Save configuration to file."""
        self.validate_config(config)
        
        config_dict = {
            'backend': config.backend,
            'maxsize': config.maxsize,
            'auto_cleanup': config.auto_cleanup,
            'timeout': config.timeout,
            'namespace': config.namespace,
            'enable_multi_tenant': config.enable_multi_tenant,
            'mmap_path': config.mmap_path,
            'ray_address': config.ray_address,
            'actor_options': config.actor_options,
            'batch_size': config.batch_size,
            'prefetch_count': config.prefetch_count,
            'enable_compression': config.enable_compression,
            'enable_metrics': config.enable_metrics,
            'log_level': config.log_level,
            'stats_interval': config.stats_interval,
            'fallback_backend': config.fallback_backend,
            'auto_fallback': config.auto_fallback
        }
        
        with open(file_path, 'w') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                yaml.dump(config_dict, f, default_flow_style=False)
            elif file_path.endswith('.json'):
                import json
                json.dump(config_dict, f, indent=2)
            else:
                raise ValueError("Output file must be .yaml, .yml, or .json")


# Global config manager instance
_config_manager = QueueConfigManager()


def get_default_config() -> QueueConfig:
    """Get default queue configuration."""
    return _config_manager.load_config()


def load_queue_config(config_path: str) -> QueueConfig:
    """Load queue configuration from file."""
    manager = QueueConfigManager()
    return manager.load_config(config_path)


def get_queue_config_from_env() -> QueueConfig:
    """Get queue configuration with environment variable overrides."""
    return _config_manager.get_config()
