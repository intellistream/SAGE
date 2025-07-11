from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, Tuple, TypeVar, Generic, get_args, get_origin
from sage_core.api.enum import PlatformType
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.filter_transformation import FilterTransformation
from sage_core.transformation.flatmap_transformation import FlatMapTransformation
from sage_core.transformation.map_transformation import MapTransformation
from sage_core.transformation.sink_transformation import SinkTransformation
from sage_core.transformation.source_transformation import SourceTransformation
from sage_core.api.base_function import BaseFunction
from .connected_streams import ConnectedStreams
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    from .env import BaseEnvironment
    from .datastream import DataStream

T = TypeVar("T")


class DataStream(Generic[T]):
    """表示单个transformation生成的流结果"""
    def __init__(self, env:BaseEnvironment, transformation: BaseTransformation):
        self.logger = CustomLogger(
            filename=f"Datastream_{transformation.function_class.__name__}",
            env_name = env.name,
            console_output="WARNING",
            file_output=True,
            global_output = "DEBUG",
        )
        self._environment = env
        self.transformation = transformation
        self._type_param = self._resolve_type_param()

        self.logger.debug(f"DataStream created with transformation: {transformation.function_class.__name__}, type_param: {self._type_param}")

    # ---------------------------------------------------------------------
    # 表示对于当前 DataStream 的变换操作，生成变换算子的第一个输出 Datastream
    # ---------------------------------------------------------------------
    def map(self, function: Type[BaseFunction], *args, **kwargs) -> "DataStream":
        tr = MapTransformation(self._environment,function,*args,**kwargs)
        return self._apply(tr)

    def filter(self, function: Type[BaseFunction],*args, **kwargs) -> "DataStream":
        tr = FilterTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)

    def flatmap(self, function: Type[BaseFunction],*args, **kwargs) -> "DataStream":
        tr = FlatMapTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)
    
    def sink(self, function: Union[BaseFunction, Type[BaseFunction]],*args, **kwargs) -> "DataStream":
        tr = SinkTransformation(self._environment,function,*args,**kwargs)
        return self._apply(tr)





    # 重做connected streams
    def connect(self, other: "DataStream") -> 'ConnectedStreams':
        """连接两个数据流，返回ConnectedStreams"""
        return ConnectedStreams(self._environment, [
            self.transformation,
            other.transformation
        ])
    
    # ---------------------------------------------------------------------
    # 内部帮助：把新 BaseTransformation 接入管线
    # ---------------------------------------------------------------------
    def _apply(self, tr: BaseTransformation) -> "DataStream":

        # 连接到第一个输入
        tr.add_upstream(self.transformation)
        
        self._environment._pipeline.append(tr)
        return DataStream(self._environment, tr)
    
    def _resolve_type_param(self):
        # 利用 __orig_class__ 捕获 T
        orig = getattr(self, "__orig_class__", None)
        if orig and get_origin(orig) == DataStream:
            return get_args(orig)[0]
        else:
            return Any  # fallback，如果泛型没有显式写就为 None