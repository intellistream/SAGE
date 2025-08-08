"""
SAGE Core API Module

Core streaming API interfaces for SAGE.
这个模块包含了所有用户需要的核心API接口。
"""

# 核心环境接口
from .base_environment import BaseEnvironment
from .local_environment import LocalEnvironment
from .remote_environment import RemoteEnvironment

# 数据流接口
from .datastream import DataStream
from .connected_streams import ConnectedStreams

# 核心函数基类
from .function.base_function import BaseFunction
from .function.batch_function import BatchFunction
from .function.map_function import MapFunction
from .function.filter_function import FilterFunction
from .function.sink_function import SinkFunction
from .function.source_function import SourceFunction
from .function.keyby_function import KeyByFunction
from .function.flatmap_function import FlatMapFunction
from .function.comap_function import BaseCoMapFunction
from .function.join_function import BaseJoinFunction

# 变换接口 (从sage-kernel导入)
try:
    from sage.core.transformation.base_transformation import BaseTransformation
    from sage.core.transformation.map_transformation import MapTransformation
    from sage.core.transformation.filter_transformation import FilterTransformation
    from sage.core.transformation.sink_transformation import SinkTransformation
    _transformations_available = True
except ImportError:
    _transformations_available = False

__all__ = [
    # 环境类
    'BaseEnvironment',
    'LocalEnvironment', 
    'RemoteEnvironment',
    
    # 数据流类
    'DataStream',
    'ConnectedStreams',
    
    # 函数类
    'BaseFunction',
    'BatchFunction',
    'MapFunction',
    'FilterFunction',
    'SinkFunction',
    'SourceFunction',
    'KeyByFunction',
    'FlatMapFunction',
    'BaseCoMapFunction',
    'BaseJoinFunction',
]

# 如果变换模块可用，添加到导出列表
if _transformations_available:
    __all__.extend([
        'BaseTransformation',
        'MapTransformation',
        'FilterTransformation', 
        'SinkTransformation',
    ])
