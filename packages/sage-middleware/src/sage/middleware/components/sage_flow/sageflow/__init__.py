"""
SAGE Flow - High-Performance Stream Processing Framework

SAGE Flow 是一个高性能的流处理框架，专为多模态数据处理和向量化而设计。
它结合了现代 C++20 的性能优势和 Python 的易用性。
"""

__version__ = "1.0.0"
__author__ = "IntelliStream Team"
__email__ = "intellistream@outlook.com"

# 导入核心C++扩展模块 - 强制使用真实引擎
try:
    from sageflow import (
        # 枚举类型
        ContentType,
        VectorDataType,
        OperatorType,

        # 核心数据类型
        VectorData,
        MultiModalMessage,

        # 流处理API
        DataStream,
        Environment,
        EnvironmentConfig,

        # 操作符
        Operator,

        # 工厂函数
        create_text_message,
        create_binary_message,

        # DataStream工厂函数
        from_list,
    )
except ImportError:
    # 如果C++扩展未加载，提供占位符
    class Placeholder:
        pass
    ContentType = VectorDataType = OperatorType = VectorData = MultiModalMessage = DataStream = Environment = EnvironmentConfig = Operator = create_text_message = create_binary_message = from_list = Placeholder

# 导入Python实用工具
from .utils import (
    configure_logging,
    get_version_info,
)

from .stream import Stream

# 公共API
__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    
    # 枚举类型
    "ContentType",
    "VectorDataType", 
    "OperatorType",
    
    # 核心数据类型
    "VectorData",
    "MultiModalMessage",
    
    # 流处理API
    "DataStream",
    "Environment",
    "EnvironmentConfig",
    
    # 操作符
    "Operator",
    
    # 工厂函数
    "create_text_message",
    "create_binary_message",

    # DataStream工厂函数
    "from_list",

    # 流处理API
    "Stream",

    # 实用工具
    "configure_logging",
    "get_version_info",
]

# 配置默认日志
configure_logging()