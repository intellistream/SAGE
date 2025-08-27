from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, Tuple, TypeVar, Generic, get_args, get_origin, Optional
from sage.core.api.function.base_function import BaseFunction
from sage.core.api.function.lambda_function import wrap_lambda, detect_lambda_type
from .connected_streams import ConnectedStreams
from sage.common.utils.logging.custom_logger import CustomLogger

if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment
    from .datastream import DataStream
    from sage.core.transformation.base_transformation import BaseTransformation
    from sage.core.transformation.filter_transformation import FilterTransformation
    from sage.core.transformation.flatmap_transformation import FlatMapTransformation
    from sage.core.transformation.map_transformation import MapTransformation
    from sage.core.transformation.sink_transformation import SinkTransformation
    from sage.core.transformation.source_transformation import SourceTransformation
    from sage.core.transformation.keyby_transformation import KeyByTransformation

T = TypeVar("T")


class DataStream(Generic[T]):
    """表示单个transformation生成的流结果"""

    def __init__(self, env: 'BaseEnvironment', transformation: 'BaseTransformation'):
        self.logger = CustomLogger()
        self._environment = env
        self.transformation = transformation
        self._type_param = self._resolve_type_param()

        self.logger.debug(
            f"DataStream created with transformation: {transformation.function_class.__name__}, type_param: {self._type_param}")

    def _get_transformation_classes(self):
        """动态导入transformation类以避免循环导入"""
        if not hasattr(self, '_transformation_classes'):
            from sage.core.transformation.base_transformation import BaseTransformation
            from sage.core.transformation.filter_transformation import FilterTransformation
            from sage.core.transformation.flatmap_transformation import FlatMapTransformation
            from sage.core.transformation.map_transformation import MapTransformation
            from sage.core.transformation.sink_transformation import SinkTransformation
            from sage.core.transformation.source_transformation import SourceTransformation
            from sage.core.transformation.keyby_transformation import KeyByTransformation
            
            self._transformation_classes = {
                'BaseTransformation': BaseTransformation,
                'FilterTransformation': FilterTransformation,
                'FlatMapTransformation': FlatMapTransformation,
                'MapTransformation': MapTransformation,
                'SinkTransformation': SinkTransformation,
                'SourceTransformation': SourceTransformation,
                'KeyByTransformation': KeyByTransformation
            }
        return self._transformation_classes

    # ---------------------------------------------------------------------
    # general datastream api
    # ---------------------------------------------------------------------
    def map(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'map')
        
        # 获取MapTransformation类
        MapTransformation = self._get_transformation_classes()['MapTransformation']
        tr = MapTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)

    def filter(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'filter')
        
        # 获取FilterTransformation类
        FilterTransformation = self._get_transformation_classes()['FilterTransformation']
        tr = FilterTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)

    def flatmap(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'flatmap')
        
        # 获取FlatMapTransformation类
        FlatMapTransformation = self._get_transformation_classes()['FlatMapTransformation']
        tr = FlatMapTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'sink')
        
        # 获取SinkTransformation类
        SinkTransformation = self._get_transformation_classes()['SinkTransformation']
        tr = SinkTransformation(self._environment, function, *args, **kwargs)
        self._apply(tr)
        return self  # sink不返回新的DataStream，因为它是终端操作

    def keyby(self, function: Union[Type[BaseFunction], callable],
              strategy: str = "hash", *args, **kwargs) -> "DataStream":
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, 'keyby')

        # 获取KeyByTransformation类
        KeyByTransformation = self._get_transformation_classes()['KeyByTransformation']
        tr = KeyByTransformation(
            self._environment,
            function,
            strategy=strategy
            , *args, **kwargs
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

    def fill_future(self, future_stream: "DataStream") -> None:
        """
        将当前数据流填充到预先声明的future stream中，创建反馈边。
        
        Args:
            future_stream: 需要被填充的future stream (通过env.from_future创建)
            
        Raises:
            ValueError: 如果目标stream不是future stream
            RuntimeError: 如果future stream已经被填充过
            
        Example:
            # 1. 声明future stream
            future_stream = env.from_future("feedback_loop")
            
            # 2. 构建pipeline，使用future stream
            result = source.connect(future_stream).comap(CombineFunction)
            
            # 3. 填充future stream，创建反馈边
            processed_result = result.filter(SomeFilter)
            processed_result.fill_future(future_stream)
        """
        from sage.core.transformation.future_transformation import FutureTransformation

        # 验证目标是future stream
        if not isinstance(future_stream.transformation, FutureTransformation):
            raise ValueError("Target stream must be a future stream created by env.from_future()")

        future_trans = future_stream.transformation

        # 检查是否已经被填充
        if future_trans.filled:
            raise RuntimeError(f"Future stream '{future_trans.future_name}' has already been filled")

        # 使用FutureTransformation的填充方法
        future_trans.fill_with_transformation(self.transformation)

        # 从环境的pipeline中移除future transformation的引用
        # 注意：不能完全删除，因为可能有其他地方引用它，但标记为已填充
        self.logger.debug(
            f"Filled future stream '{future_trans.future_name}' with transformation '{self.transformation.basename}'")

        # 记录反馈边的创建
        self.logger.info(f"Created feedback edge: {self.transformation.basename} -> {future_trans.future_name}")

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
        from sage.libs.io_utils.sink import PrintSink
        return self.sink(PrintSink, prefix=prefix, separator=separator, colored=colored)

    # ---------------------------------------------------------------------
    # internel methods
    # ---------------------------------------------------------------------
    def _apply(self, tr: BaseTransformation) -> "DataStream":
        # 连接到输入索引0（单输入情况）
        tr.add_upstream(self.transformation, input_index=0)

        self._environment.pipeline.append(tr)
        return DataStream(self._environment, tr)

    def _resolve_type_param(self):
        # 利用 __orig_class__ 捕获 T
        orig = getattr(self, "__orig_class__", None)
        if orig and get_origin(orig) == DataStream:
            return get_args(orig)[0]
        else:
            return Any  # fallback，如果泛型没有显式写就为 None
