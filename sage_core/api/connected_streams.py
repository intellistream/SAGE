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
    
    def comap(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> 'DataStream':
        """
        Apply a CoMap function that processes each connected stream separately
        
        CoMap (Co-processing Map) enables parallel processing of multiple input streams
        where each stream is processed independently using dedicated mapN methods.
        Unlike regular map operations that merge all inputs, comap maintains stream
        boundaries and routes each input to its corresponding mapN method.
        
        Args:
            function: CoMap function class that implements map0, map1, ..., mapN methods.
                     Must inherit from BaseCoMapFunction and have is_comap=True.
            *args: Additional arguments passed to the CoMap function constructor
            **kwargs: Additional keyword arguments passed to the CoMap function constructor
            
        Returns:
            DataStream: Result stream from coordinated processing of all input streams
            
        Raises:
            NotImplementedError: Lambda functions are not supported for comap operations
            ValueError: If function is not a valid CoMap function
            
        Example:
            ```python
            class ProcessorCoMap(BaseCoMapFunction):
                def map0(self, data):
                    return f"Stream 0: {data}"
                
                def map1(self, data):
                    return f"Stream 1: {data * 2}"
            
            result = (stream1
                .connect(stream2)
                .comap(ProcessorCoMap)
                .print("CoMap Result"))
            ```
        """
        if callable(function) and not isinstance(function, type):
            # Lambda functions need special wrapper - not implemented yet
            raise NotImplementedError(
                "Lambda functions are not supported for comap operations. "
                "Please use a class that inherits from BaseCoMapFunction."
            )
        
        # Import CoMapTransformation (delayed import to avoid circular dependencies)
        from sage_core.transformation.comap_transformation import CoMapTransformation
        
        # Validate input stream count before creating transformation
        input_stream_count = len(self.transformations)
        if input_stream_count < 2:
            raise ValueError(
                f"CoMap operations require at least 2 input streams, "
                f"but only {input_stream_count} streams provided."
            )
        
        # Create CoMapTransformation
        tr = CoMapTransformation(self._environment, function, *args, **kwargs)
        
        # Validate that the function supports the number of input streams
        tr.validate_input_streams(input_stream_count)
        
        return self._apply(tr)

    def keyby(self, 
             key_selector: Union[Type[BaseFunction], List[Type[BaseFunction]]], 
             strategy: str = "hash") -> 'ConnectedStreams':
        """
        Apply keyby partitioning to connected streams using composition approach
        
        Args:
            key_selector: 
                - Single BaseFunction: Apply same key extraction to all streams
                - List[BaseFunction]: Apply different key extraction per stream (Flink-style)
            strategy: Partitioning strategy ("hash", "broadcast", "round_robin")
            
        Returns:
            ConnectedStreams: New ConnectedStreams with all streams keyed
            
        Example:
            ```python
            # Same key selector for all streams
            keyed_streams = stream1.connect(stream2).keyby(UserIdExtractor)
            
            # Different key selector per stream (Flink-style)
            keyed_streams = stream1.connect(stream2).keyby([UserIdExtractor, SessionIdExtractor])
            
            # Continue with further operations
            result = keyed_streams.comap(JoinFunction).sink(OutputSink)
            ```
        """
        if callable(key_selector) and not isinstance(key_selector, type):
            raise NotImplementedError(
                "Lambda functions are not supported for keyby operations. "
                "Please use KeyByFunction classes."
            )
        
        from .datastream import DataStream
        
        input_stream_count = len(self.transformations)
        
        if isinstance(key_selector, list):
            # Flink-style: different key selector per stream
            if len(key_selector) != input_stream_count:
                raise ValueError(
                    f"Key selector count ({len(key_selector)}) must match stream count ({input_stream_count})"
                )
            
            # 为每个流分别应用keyby
            keyed_transformations = []
            for transformation, selector in zip(self.transformations, key_selector):
                # 创建单独的DataStream并应用keyby
                individual_stream = DataStream(self._environment, transformation)
                keyed_stream = individual_stream.keyby(selector, strategy=strategy)
                keyed_transformations.append(keyed_stream.transformation)
            
        else:
            # 统一的key selector：为所有流应用相同的keyby
            keyed_transformations = []
            for transformation in self.transformations:
                # 创建单独的DataStream并应用keyby
                individual_stream = DataStream(self._environment, transformation)
                keyed_stream = individual_stream.keyby(key_selector, strategy=strategy)
                keyed_transformations.append(keyed_stream.transformation)
        
        # 返回新的ConnectedStreams，包含所有keyed transformations
        return ConnectedStreams(self._environment, keyed_transformations)

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