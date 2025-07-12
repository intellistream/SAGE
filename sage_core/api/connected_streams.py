from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, TypeVar, Generic, get_args, get_origin, Callable
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.map_transformation import MapTransformation
from sage_core.transformation.sink_transformation import SinkTransformation
from sage_core.function.base_function import BaseFunction
from sage_core.function.lambda_function import wrap_lambda
from sage_core.function.comap_function import BaseCoMapFunction
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
    
    def comap(self, function: Union[Type[BaseFunction], callable, List[callable]], *args, **kwargs) -> 'DataStream':
        """
        Apply a CoMap function that processes each connected stream separately
        
        CoMap (Co-processing Map) enables parallel processing of multiple input streams
        where each stream is processed independently using dedicated mapN methods.
        Unlike regular map operations that merge all inputs, comap maintains stream
        boundaries and routes each input to its corresponding mapN method.
        
        Args:
            function: One of the following:
                - CoMap function class that implements map0, map1, ..., mapN methods (class-based)
                - List of callables [func0, func1, ..., funcN] (lambda list)
                - Single callable for multiple function arguments (lambda args)
            *args: When function is a class, additional constructor arguments.
                   When function is callable(s), treated as additional functions.
            **kwargs: When function is a class, additional constructor arguments.
                     When function is callable(s), ignored with warning.
            
        Returns:
            DataStream: Result stream from coordinated processing of all input streams
            
        Raises:
            ValueError: If function input is invalid or function count doesn't match stream count
            
        Examples:
            Class-based approach:
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
            
            Lambda list approach:
            ```python
            result = (stream1
                .connect(stream2)
                .comap([
                    lambda x: f"Stream 0: {x}",
                    lambda x: f"Stream 1: {x * 2}"
                ])
                .print("Lambda CoMap"))
            ```
            
            Multiple arguments approach:
            ```python
            def process_stream_0(data):
                return f"Stream 0: {data}"
            
            result = (stream1
                .connect(stream2)
                .comap(
                    process_stream_0,
                    lambda x: f"Stream 1: {x * 2}"
                )
                .print("Mixed CoMap"))
            ```
        """
        # Validate minimum input stream count
        input_stream_count = len(self.transformations)
        if input_stream_count < 2:
            raise ValueError(
                f"CoMap operations require at least 2 input streams, "
                f"but only {input_stream_count} streams provided."
            )
        
        # Parse function input and determine approach
        comap_function, final_args, final_kwargs = self._parse_comap_functions(
            function, input_stream_count, *args, **kwargs
        )
        
        # Import CoMapTransformation (delayed import to avoid circular dependencies)
        from sage_core.transformation.comap_transformation import CoMapTransformation
        
        # Create CoMapTransformation
        tr = CoMapTransformation(self._environment, comap_function, *final_args, **final_kwargs)
        
        # Validate that the function supports the number of input streams
        tr.validate_input_streams(input_stream_count)
        
        return self._apply(tr)

    # ---------------------------------------------------------------------
    # CoMap function parsing methods
    # ---------------------------------------------------------------------
    def _parse_comap_functions(self, function: Union[Type[BaseFunction], callable, List[callable]], 
                              input_stream_count: int, *args, **kwargs) -> tuple:
        """
        Parse different input formats for CoMap functions and return standardized format
        
        Args:
            function: The function input (class, callable, or list of callables)
            input_stream_count: Number of input streams requiring processing
            *args: Additional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            tuple: (comap_function_class, final_args, final_kwargs)
        """
        # Case 1: Class-based CoMap function (existing approach)
        if isinstance(function, type) and issubclass(function, BaseCoMapFunction):
            return function, args, kwargs
        
        # Case 2: List of functions
        if isinstance(function, list):
            if args or kwargs:
                self._warn_ignored_params("args/kwargs", args, kwargs)
            return self._create_dynamic_comap_class(function, input_stream_count), (), {}
        
        # Case 3: Multiple function arguments (callables passed as separate args)
        if callable(function):
            # Collect all callable arguments
            all_functions = [function] + [arg for arg in args if callable(arg)]
            non_callable_args = [arg for arg in args if not callable(arg)]
            
            if non_callable_args or kwargs:
                self._warn_ignored_params("non-callable args/kwargs", non_callable_args, kwargs)
            
            return self._create_dynamic_comap_class(all_functions, input_stream_count), (), {}
        
        # Case 4: Invalid input
        raise ValueError(
            f"Invalid function input for comap: {type(function)}. "
            f"Expected: CoMap class, callable, or list of callables."
        )
    
    def _create_dynamic_comap_class(self, function_list: List[callable], input_stream_count: int) -> Type[BaseCoMapFunction]:
        """
        Dynamically create a CoMap class from a list of functions
        
        Args:
            function_list: List of callable functions
            input_stream_count: Expected number of input streams
            
        Returns:
            Type[BaseCoMapFunction]: Dynamically generated CoMap class
        """
        # Validate function count matches input stream count
        if len(function_list) != input_stream_count:
            raise ValueError(
                f"Number of functions ({len(function_list)}) must match "
                f"number of input streams ({input_stream_count}). "
                f"Please provide exactly {input_stream_count} functions."
            )
        
        # Validate all items are callable
        for i, func in enumerate(function_list):
            if not callable(func):
                raise ValueError(f"Item at index {i} is not callable: {type(func).__name__}")
        
        # Create the dynamic class with all required methods defined inline
        # We need to create a class dynamically with the required mapN methods
        
        # Create method definitions for dynamic class
        class_methods = {
            '__init__': lambda self: BaseCoMapFunction.__init__(self),
            'is_comap': property(lambda self: True),
            'execute': lambda self, data: self._raise_execute_error(),
            '_raise_execute_error': lambda self: self._do_raise_execute_error(),
            '_do_raise_execute_error': lambda self: (_ for _ in ()).throw(
                NotImplementedError("CoMap functions use mapN methods, not execute()")
            )
        }
        
        # Add all required mapN methods
        for i, func in enumerate(function_list):
            method_name = f"map{i}"
            # Create method that captures the function in closure
            class_methods[method_name] = (lambda f: lambda self, data: f(data))(func)
        
        # Create the dynamic class
        DynamicCoMapFunction = type(
            'DynamicCoMapFunction',
            (BaseCoMapFunction,),
            class_methods
        )
        
        return DynamicCoMapFunction
    
    def _warn_ignored_params(self, param_type: str, *params) -> None:
        """
        Warn user about ignored parameters in lambda/callable CoMap usage
        
        Args:
            param_type: Description of ignored parameter type
            *params: The ignored parameters
        """
        if any(params):
            print(f"⚠️  Warning: {param_type} ignored in lambda/callable CoMap usage: {params}")

    # ---------------------------------------------------------------------
    # internal methods
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