from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, TypeVar, Generic, get_args, get_origin
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.map_transformation import MapTransformation
from sage_core.transformation.sink_transformation import SinkTransformation
from sage_core.function.base_function import BaseFunction
from sage_core.function.lambda_function import wrap_lambda
if TYPE_CHECKING:
    from .datastream import DataStream
    from .env import BaseEnvironment

class ConnectedStreams:
    """表示多个transformation连接后的流结果"""
    def __init__(self, env: 'BaseEnvironment', transformations: List[BaseTransformation]):
        self._environment = env
        self.transformations = transformations

    # ---------------------------------------------------------------------
    # general datastream api
    # ---------------------------------------------------------------------
    def map(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> 'DataStream':
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'map')
        tr = MapTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> 'DataStream':
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'sink')
        tr = SinkTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)

    def print(self, prefix: str = "", separator: str = " | ", colored: bool = True) -> 'DataStream':
        """
        便捷的打印方法 - 将连接的数据流输出到控制台
        
        Args:
            prefix: 输出前缀，默认为空
            separator: 前缀与内容之间的分隔符，默认为 " | " 
            colored: 是否启用彩色输出，默认为True
            
        Returns:
            DataStream: 返回新的数据流用于链式调用
        """
        from sage_common_funs.io.sink import PrintSink
        return self.sink(PrintSink, prefix=prefix, separator=separator, colored=colored)

    def connect(self, other: Union['DataStream', 'ConnectedStreams']) -> 'ConnectedStreams':
        """连接更多数据流
        
        Args:
            other: 另一个DataStream或ConnectedStreams实例
            
        Returns:
            ConnectedStreams: 新的连接流，按顺序包含所有transformation
        """
        if hasattr(other, 'transformation'):  # DataStream
            # ConnectedStreams + DataStream -> ConnectedStreams
            new_transformations = self.transformations + [other.transformation]
        else:  # ConnectedStreams
            # ConnectedStreams + ConnectedStreams -> ConnectedStreams
            new_transformations = self.transformations + other.transformations
        
        return ConnectedStreams(self._environment, new_transformations)
    
    # ---------------------------------------------------------------------
    # internel methods
    # ---------------------------------------------------------------------
    def _apply(self, tr: BaseTransformation) -> 'DataStream':
        """将新 BaseTransformation 接入管线"""
        from .datastream import DataStream
        
        # 检查是否为comap操作（分别处理多个输入）
        if hasattr(tr.function_class, 'is_comap') and tr.function_class.is_comap:
            # comap操作：分别连接每个上游transformation到不同的输入索引
            for input_index, upstream_trans in enumerate(self.transformations):
                tr.add_upstream(upstream_trans, input_index=input_index)
        else:
            # 常规操作：所有上游transformation合并到输入索引0
            for upstream_trans in self.transformations:
                tr.add_upstream(upstream_trans, input_index=0)

        self._environment._pipeline.append(tr)
        return DataStream(self._environment, tr)