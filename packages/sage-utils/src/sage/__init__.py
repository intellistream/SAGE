"""
SAGE Utils - 通用工具库
=====================

为SAGE框架提供基础的配置管理、日志记录等功能。

模块:
----
- config: 配置文件加载和管理
- logging: 自定义日志记录功能

Examples:
--------
>>> from sage.utils.config.loader import load_config
>>> from sage.utils.logging.custom_logger import CustomLogger
>>> 
>>> # 加载配置
>>> config = load_config("config.yaml")
>>> 
>>> # 创建日志记录器
>>> logger = CustomLogger([("console", "INFO")], name="MyApp")
>>> logger.info("应用启动")
"""

__version__ = "0.1.0"

# 版本信息
VERSION = __version__
VERSION_INFO = tuple(int(x) for x in __version__.split('.'))

# 元数据
__title__ = "intellistream-sage-utils"
__description__ = "SAGE Framework - 通用工具库，包含配置管理、日志记录等基础功能"
__author__ = "IntelliStream Team"
__author_email__ = "intellistream@outlook.com"
__license__ = "MIT"
__url__ = "https://github.com/intellistream/SAGE"

# 公开接口 - 方便直接导入常用功能
from sage.utils.config.loader import load_config
from sage.utils.config.manager import ConfigManager, BaseConfig, save_config
from sage.utils.logging.custom_logger import CustomLogger
from sage.utils.logging.custom_formatter import CustomFormatter

__all__ = [
    # 版本信息
    "__version__",
    "VERSION", 
    "VERSION_INFO",
    
    # 配置管理
    "load_config",
    "save_config", 
    "ConfigManager",
    "BaseConfig",
    
    # 日志记录
    "CustomLogger",
    "CustomFormatter",
]
