from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from sage.common.core import (
    BaseCoMapFunction,
    BaseFunction,
    BaseJoinFunction,
    wrap_lambda,
)
from sage.kernel.api.base_environment import BaseEnvironment
from sage.kernel.api.transformation.join_transformation import JoinTransformation

if TYPE_CHECKING:
    from sage.kernel.api.transformation.base_transformation import BaseTransformation

    from .datastream import DataStream


class ConnectedStreams:
    """
    表示多个数据流的连接，类似于Flink的ConnectedStreams

    这个类建模了多个数据流之间的逻辑连接关系，保持每个流的独立性，
    直到应用CoMap等多流操作时才进行实际的数据合并处理。

    设计原则：
    1. 保持流的边界信息，直到真正需要合并时
    2. 每个连接的流保持其独立的transformation身份
    3. 只有在应用多流操作（如comap）时才创建多输入的transformation
    """

    def __init__(self, env: BaseEnvironment, transformations: list[BaseTransformation]):
        self._environment = env
        self.transformations = transformations

        # 验证输入
        if len(transformations) < 2:
            raise ValueError("ConnectedStreams requires at least 2 transformations")

        # 确保所有transformation都来自同一个环境
        for trans in transformations:
            if trans.env != env:
                raise ValueError("All transformations must be from the same environment")

    def _get_transformation_classes(self):
        """动态导入transformation类以避免循环导入"""
        if not hasattr(self, "_transformation_classes"):
            from sage.kernel.api.transformation.base_transformation import (
                BaseTransformation,
            )
            from sage.kernel.api.transformation.join_transformation import (
                JoinTransformation,
            )
            from sage.kernel.api.transformation.map_transformation import (
                MapTransformation,
            )
            from sage.kernel.api.transformation.sink_transformation import (
                SinkTransformation,
            )

            self._transformation_classes = {
                "BaseTransformation": BaseTransformation,
                "MapTransformation": MapTransformation,
                "SinkTransformation": SinkTransformation,
                "JoinTransformation": JoinTransformation,
            }
        return self._transformation_classes

    def map(
        self,
        function: type[BaseFunction] | Callable,
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, "map")

        # 使用传入的parallelism或者默认值1
        actual_parallelism = parallelism if parallelism is not None else 1

        # 获取MapTransformation类
        MapTransformation = self._get_transformation_classes()["MapTransformation"]
        tr = MapTransformation(
            self._environment, function, *args, parallelism=actual_parallelism, **kwargs
        )
        return self._apply(tr)

    def sink(
        self,
        function: type[BaseFunction] | Callable,
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, "sink")

        # 使用传入的parallelism或者默认值1
        actual_parallelism = parallelism if parallelism is not None else 1

        # 获取SinkTransformation类
        SinkTransformation = self._get_transformation_classes()["SinkTransformation"]
        tr = SinkTransformation(
            self._environment, function, *args, parallelism=actual_parallelism, **kwargs
        )
        return self._apply(tr)

    def print(self, prefix: str = "", separator: str = " | ", colored: bool = True) -> DataStream:
        """
        便捷的打印方法 - 将连接的数据流输出到控制台

        Args:
            prefix: 输出前缀，默认为空
            separator: 前缀与内容之间的分隔符，默认为 " | "
            colored: 是否启用彩色输出，默认为True

        Returns:
            DataStream: 返回新的数据流用于链式调用
        """
        from sage.common.components.debug.print_sink import PrintSink

        return self.sink(PrintSink, prefix=prefix, separator=separator, colored=colored)

    def connect(self, other: DataStream | ConnectedStreams) -> ConnectedStreams:
        """连接更多数据流

        Args:
            other: 另一个DataStream或ConnectedStreams实例

        Returns:
            ConnectedStreams: 新的连接流，按顺序包含所有transformation
        """
        if hasattr(other, "transformation"):  # DataStream
            # ConnectedStreams + DataStream -> ConnectedStreams
            new_transformations = self.transformations + [other.transformation]  # type: ignore[attr-defined]
        else:  # ConnectedStreams
            # ConnectedStreams + ConnectedStreams -> ConnectedStreams
            new_transformations = self.transformations + other.transformations  # type: ignore[attr-defined]

        return ConnectedStreams(self._environment, new_transformations)

    def comap(
        self,
        function: type[BaseFunction] | Callable,
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
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
            NotImplementedError: Lambda functions are not supported for comap operations
            TypeError: If function is not a valid CoMap function
            ValueError: If function doesn't support the required number of input streams

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
        """
        if callable(function) and not isinstance(function, type):
            # Lambda functions need special wrapper - not implemented yet
            raise NotImplementedError(
                "Lambda functions are not supported for comap operations. "
                "Please use a class that inherits from BaseCoMapFunction."
            )

        # Validate input stream count before creating transformation
        input_stream_count = len(self.transformations)
        if input_stream_count < 2:
            raise ValueError(
                f"CoMap operations require at least 2 input streams, "
                f"but only {input_stream_count} streams provided."
            )

        # Import BaseCoMapFunction for type checking
        from sage.common.core import BaseCoMapFunction

        # Type validation: Check if function is a proper CoMap function
        if not isinstance(function, type):
            raise TypeError(
                f"CoMap function must be a class, got {type(function).__name__}. "
                f"Please provide a class that inherits from BaseCoMapFunction."
            )

        if not issubclass(function, BaseCoMapFunction):
            raise TypeError(
                f"Function {function.__name__} must inherit from BaseCoMapFunction. "
                f"CoMap operations require CoMap function with mapN methods."
            )

        # Validate that function supports the required number of input streams
        required_methods = [f"map{i}" for i in range(input_stream_count)]
        missing_methods = []

        for method_name in required_methods:
            if not hasattr(function, method_name):
                missing_methods.append(method_name)

        if missing_methods:
            raise TypeError(
                f"CoMap function {function.__name__} is missing required methods: {missing_methods}. "
                f"For {input_stream_count} input streams, the function must implement: {required_methods}."
            )

        # Additional validation: Check if mapN methods are callable
        for method_name in required_methods:
            method = getattr(function, method_name)
            if not callable(method):
                raise TypeError(
                    f"CoMap function {function.__name__}.{method_name} must be callable. "
                    f"Found {type(method).__name__} instead."
                )

        # Import CoMapTransformation (delayed import to avoid circular dependencies)
        from sage.kernel.api.transformation.comap_transformation import (
            CoMapTransformation,
        )

        # 使用传入的parallelism或者之前设置的hint
        actual_parallelism = parallelism if parallelism is not None else 1

        # Create CoMapTransformation
        tr = CoMapTransformation(
            self._environment, function, *args, parallelism=actual_parallelism, **kwargs
        )

        # Additional validation at transformation level
        tr.validate_input_streams(input_stream_count)

        return self._apply(tr)

    # 在 connected_streams.py 中添加简化的join方法
    def join(
        self,
        function: type[BaseJoinFunction] | Callable,
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
        """
        Join two keyed streams using a join function.

        Args:
            function: Join function class implementing BaseJoinFunction
            *args, **kwargs: Arguments passed to join function constructor

        Returns:
            DataStream: Stream of join results

        Example:
            ```python
            class UserOrderJoin(BaseJoinFunction):
                def execute(self, payload, key, tag):
                    # tag 0: user data, tag 1: order data
                    # 实现join逻辑并返回结果列表
                    return [joined_result] if match else []

            result = (user_stream
                .keyby(lambda x: x["user_id"])
                .connect(order_stream.keyby(lambda x: x["user_id"]))
                .join(UserOrderJoin)
                .print("Join Results"))
            ```
        """
        # 验证输入
        if len(self.transformations) != 2:
            raise ValueError(
                f"Join requires exactly 2 input streams, got {len(self.transformations)}"
            )

        # 类型检查
        if not isinstance(function, type) or not issubclass(function, BaseJoinFunction):
            raise TypeError("Join function must inherit from BaseJoinFunction")

        # TODO: 验证流都是keyed的
        # Issue URL: https://github.com/intellistream/SAGE/issues/225
        # self._validate_keyed_streams()

        # 创建transformation
        # 使用传入的parallelism或者默认值1
        actual_parallelism = parallelism if parallelism is not None else 1
        join_tr = JoinTransformation(
            self._environment, function, *args, parallelism=actual_parallelism, **kwargs
        )
        return self._apply(join_tr)

    def keyby(
        self,
        key_selector: type[BaseFunction] | list[type[BaseFunction]],
        strategy: str = "hash",
    ) -> ConnectedStreams:
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
            for transformation, selector in zip(self.transformations, key_selector, strict=False):
                # 创建单独的DataStream并应用keyby
                individual_stream: DataStream = DataStream(self._environment, transformation)
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
    # CoMap function parsing methods
    # ---------------------------------------------------------------------
    def _parse_comap_functions(
        self,
        function: type[BaseFunction] | Callable | list[Callable],
        input_stream_count: int,
        *args,
        **kwargs,
    ) -> tuple:
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
            return (
                self._create_dynamic_comap_class(function, input_stream_count),
                (),
                {},
            )

        # Case 3: Multiple function arguments (callables passed as separate args)
        if callable(function):
            # Collect all callable arguments
            all_functions = [function] + [arg for arg in args if callable(arg)]
            non_callable_args = [arg for arg in args if not callable(arg)]

            if non_callable_args or kwargs:
                self._warn_ignored_params("non-callable args/kwargs", non_callable_args, kwargs)

            return (
                self._create_dynamic_comap_class(all_functions, input_stream_count),
                (),
                {},
            )

        # Case 4: Invalid input
        raise ValueError(
            f"Invalid function input for comap: {type(function)}. "
            f"Expected: CoMap class, callable, or list of callables."
        )

    def _create_dynamic_comap_class(
        self, function_list: list[Callable], input_stream_count: int
    ) -> type[BaseCoMapFunction]:
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
            "__init__": lambda self: BaseCoMapFunction.__init__(self),
            "is_comap": property(lambda self: True),
            "execute": lambda self, data: self._raise_execute_error(),
            "_raise_execute_error": lambda self: self._do_raise_execute_error(),
            "_do_raise_execute_error": lambda self: (_ for _ in ()).throw(
                NotImplementedError("CoMap functions use mapN methods, not execute()")
            ),
        }

        # Add all required mapN methods
        for i, func in enumerate(function_list):
            method_name = f"map{i}"
            # Create method that captures the function in closure
            class_methods[method_name] = (lambda f: lambda self, data: f(data))(func)

        # Create the dynamic class
        dynamic_comap_function = type("dynamic_comap_function", (BaseCoMapFunction,), class_methods)

        return dynamic_comap_function

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
    def _apply(self, tr: BaseTransformation) -> DataStream:
        """
        将多输入transformation应用到连接的流上

        这是Flink风格的实现：
        1. 新的transformation是一个多输入操作符
        2. 每个上游流连接到操作符的特定输入索引
        3. 操作符知道如何根据input_index路由数据到对应的处理方法
        """
        from .datastream import DataStream

        # 为多输入transformation设置上游连接
        # 每个上游transformation连接到特定的input_index
        for input_index, upstream_trans in enumerate(self.transformations):
            tr.add_upstream(upstream_trans, input_index=input_index)

        # 将新transformation添加到pipeline
        self._environment.pipeline.append(tr)
        return DataStream(self._environment, tr)
