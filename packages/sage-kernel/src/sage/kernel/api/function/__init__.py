"""
SAGE Kernel API - Function Definitions

提供各种用户自定义函数的基类：
- MapFunction: 一对一映射
- FlatMapFunction: 一对多映射
- FilterFunction: 过滤
- BatchFunction: 批处理
- SinkFunction: 输出
- SourceFunction: 数据源
"""

# 导入核心函数基类（sage-apps实际使用的）
from .batch_function import BatchFunction
from .filter_function import FilterFunction
from .flatmap_function import FlatMapFunction
from .map_function import MapFunction
from .sink_function import SinkFunction
from .source_function import SourceFunction

# 版本信息
try:
    from sage.kernel._version import __author__, __email__, __version__
except ImportError:
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "BatchFunction",
    "FilterFunction",
    "FlatMapFunction",
    "MapFunction",
    "SinkFunction",
    "SourceFunction",
]

