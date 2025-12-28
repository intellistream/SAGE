"""配置与参数管理

提供配置加载和命令行参数解析：
- RuntimeConfig: 运行时配置管理器
- get_required_config: 必需配置校验
- parse_args: 命令行参数解析
"""

from .args_parser import parse_args
from .config_loader import RuntimeConfig, get_required_config

__all__ = [
    "RuntimeConfig",
    "get_required_config",
    "parse_args",
]
