from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, Tuple, TypeVar, Generic, get_args, get_origin
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.map_transformation import MapTransformation
from sage_core.transformation.sink_transformation import SinkTransformation
from sage_core.function.base_function import BaseFunction
if TYPE_CHECKING:
    from .datastream import DataStream
    from .env import BaseEnvironment

# TODO: 重做
# Issue URL: https://github.com/intellistream/SAGE/issues/146
class ConnectedStreams:
    """表示多个transformation连接后的流结果"""
    def __init__(self, env:'BaseEnvironment', transformations: List[Tuple[BaseTransformation, str]]):
        self._environment = env
        self.transformations = transformations

    def _apply(self, tr: BaseTransformation) -> 'DataStream':
        """将新 BaseTransformation 接入管线"""
        declared_inputs = tr.function_class.declare_inputs()
        
        if len(self.transformations) > len(declared_inputs):
            raise ValueError(
                f"Too many upstream connections: "
                f"{len(self.transformations)} provided vs {len(declared_inputs)} expected in {tr.function_class.__name__}"
            )

        # 按顺序连接每个上游transformation到对应的输入
        for (upstream_trans, output_tag), (input_tag, input_type) in zip(self.transformations, declared_inputs):
            tr.add_upstream(input_tag=input_tag, upstream_trans=upstream_trans, upstream_tag=output_tag)

        return self._environment._append(tr)

    def map(self, function: Union[BaseFunction, Type[BaseFunction]], *args, **kwargs) -> 'DataStream':
        tr = MapTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[BaseFunction, Type[BaseFunction]], *args, **kwargs) -> 'DataStream':
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
        """连接更多数据流"""
        if isinstance(other, DataStream):
            new_transformations = self.transformations + [(other.transformation, other.output_tag)]
        else:  # ConnectedStreams
            new_transformations = self.transformations + other.transformations
        
        return ConnectedStreams(self._environment, new_transformations)