"""
SAGE Kernel API Module

Core streaming API interfaces for SAGE kernel.
这个模块包含了所有外部模块需要的核心API接口。
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