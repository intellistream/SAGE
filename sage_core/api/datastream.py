from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, Tuple, TypeVar, Generic, get_args, get_origin
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.filter_transformation import FilterTransformation
from sage_core.transformation.flatmap_transformation import FlatMapTransformation
from sage_core.transformation.map_transformation import MapTransformation
from sage_core.transformation.sink_transformation import SinkTransformation
from sage_core.transformation.source_transformation import SourceTransformation
from sage_core.transformation.keyby_transformation import KeyByTransformation
from sage_core.function.base_function import BaseFunction
from sage_core.function.lambda_function import wrap_lambda, detect_lambda_type
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
    # general datastream api
    # ---------------------------------------------------------------------
    def map(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'map')
        tr = MapTransformation(self._environment,function,*args,**kwargs)
        return self._apply(tr)

    def filter(self, function: Union[Type[BaseFunction], callable],*args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'filter')
        tr = FilterTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)

    def flatmap(self, function: Union[Type[BaseFunction], callable],*args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'flatmap')
        tr = FlatMapTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)
    
    def sink(self, function: Union[Type[BaseFunction], callable],*args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'sink')
        tr = SinkTransformation(self._environment,function,*args,**kwargs)
        return self._apply(tr)


    def keyby(self, function: Union[Type[BaseFunction], callable], 
            strategy: str = "hash",*args, **kwargs) -> "DataStream":
        """
        Apply keyby transformation that partitions data based on extracted keys
        
        Args:
            function: BaseFunction class that extracts partition key
            strategy: Partitioning strategy ("hash", "round_robin", "broadcast")
            
        Returns:
            DataStream: New stream with keyby transformation applied
            
        Example:
            ```python
            class UserIdExtractor(BaseFunction):
                def execute(self, data):
                    return data.user_id
                    
            stream.keyby(UserIdExtractor).map(UserProcessor)
            ```
        """
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'keyby')
            
        tr = KeyByTransformation(
            self._environment, 
            function, 
            strategy=strategy
            ,*args, **kwargs
        )
        return self._apply(tr)



    def connect(self, other: Union["DataStream", "ConnectedStreams"]) -> 'ConnectedStreams':
        """连接两个数据流，返回ConnectedStreams
        
        Args:
            other: 另一个DataStream或ConnectedStreams实例
            
        Returns:
            ConnectedStreams: 新的连接流，按顺序包含所有transformation
        """
        if isinstance(other, DataStream):
            # DataStream + DataStream -> ConnectedStreams
            return ConnectedStreams(self._environment, [
                self.transformation,
                other.transformation
            ])
        else:  # ConnectedStreams
            # DataStream + ConnectedStreams -> ConnectedStreams
            new_transformations = [self.transformation] + other.transformations
            return ConnectedStreams(self._environment, new_transformations)
    
    # ---------------------------------------------------------------------
    # quick helper api
    # ---------------------------------------------------------------------
    def print(self, prefix: str = "", separator: str = " | ", colored: bool = True) -> "DataStream":
        """
        便捷的打印方法 - 将数据流输出到控制台
        
        这是 sink(PrintSink, ...) 的简化版本，提供快速调试和查看数据流内容的能力
        
        Args:
            prefix: 输出前缀，默认为空
            separator: 前缀与内容之间的分隔符，默认为 " | " 
            colored: 是否启用彩色输出，默认为True
            
        Returns:
            DataStream: 返回新的数据流用于链式调用
            
        Example:
            ```python
            stream.map(some_function).print("Debug").sink(FileSink, config)
            stream.print("结果: ")  # 带前缀打印
            stream.print()  # 简单打印
            ```
        """
        from sage_common_funs.io.sink import PrintSink
        return self.sink(PrintSink, prefix=prefix, separator=separator, colored=colored)




    # ---------------------------------------------------------------------
    # internel methods
    # ---------------------------------------------------------------------
    def _apply(self, tr: BaseTransformation) -> "DataStream":
        # 连接到输入索引0（单输入情况）
        tr.add_upstream(self.transformation, input_index=0)
        
        self._environment._pipeline.append(tr)
        return DataStream(self._environment, tr)
    
    def _resolve_type_param(self):
        # 利用 __orig_class__ 捕获 T
        orig = getattr(self, "__orig_class__", None)
        if orig and get_origin(orig) == DataStream:
            return get_args(orig)[0]
        else:
            return Any  # fallback，如果泛型没有显式写就为 None