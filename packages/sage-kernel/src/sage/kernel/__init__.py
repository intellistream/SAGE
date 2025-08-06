"""
SAGE Kernel Module

Core kernel functionality for SAGE streaming system.
"""

# 导入所有核心API接口供外部模块使用
from .api import (
    # 环境类
    BaseEnvironment,
    LocalEnvironment,
    RemoteEnvironment,
    
    # 数据流类  
    DataStream,
    ConnectedStreams,
    
    # 函数类
    BaseFunction,
    BatchFunction,
    MapFunction,
    FilterFunction,
    SinkFunction,
    SourceFunction,
    KeyByFunction,
    FlatMapFunction,
    BaseCoMapFunction,
    BaseJoinFunction,
)

# 导入核心kernel组件 (内部使用)
try:
    from .kernels.core.pipeline import Pipeline
    from .kernels.jobmanager.job_manager import JobManager
    from .kernels.jobmanager.jobmanager_client import JobManagerClient
    _internal_available = True
except ImportError:
    _internal_available = False

__all__ = [
    # 公共API - 其他模块主要使用这些
    'BaseEnvironment',
    'LocalEnvironment', 
    'RemoteEnvironment',
    'DataStream',
    'ConnectedStreams',
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

# 内部组件 (有条件导出)
if _internal_available:
    __all__.extend([
        'Pipeline',
        'JobManager', 
        'JobManagerClient',
    ])

__version__ = "0.1.0"
