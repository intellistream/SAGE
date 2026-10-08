from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from sage.foundation import (
    BaseCoMapFunction,
    BaseFunction,
    BaseJoinFunction,
    PrintSink,
    wrap_lambda,
)

from ._kernel_bindings import (
    BaseTransformation,
    CoMapTransformation,
    JoinTransformation,
    MapTransformation,
    SinkTransformation,
)

if TYPE_CHECKING:
    from sage.runtime.base_environment import BaseEnvironment

    from .datastream import DataStream


class ConnectedStreams:
    """Represents logical composition of multiple streams."""

    def __init__(self, env: BaseEnvironment, transformations: list[BaseTransformation]):
        self._environment = env
        self.transformations = transformations

        if len(transformations) < 2:
            raise ValueError("ConnectedStreams requires at least 2 transformations")

        for trans in transformations:
            if trans.env != env:
                raise ValueError("All transformations must be from the same environment")

    def _get_transformation_classes(self):
        if not hasattr(self, "_transformation_classes"):
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

        actual_parallelism = parallelism if parallelism is not None else 1
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

        actual_parallelism = parallelism if parallelism is not None else 1
        SinkTransformation = self._get_transformation_classes()["SinkTransformation"]
        tr = SinkTransformation(
            self._environment, function, *args, parallelism=actual_parallelism, **kwargs
        )
        return self._apply(tr)

    def print(self, prefix: str = "", separator: str = " | ", colored: bool = True) -> DataStream:
        return self.sink(PrintSink, prefix=prefix, separator=separator, colored=colored)

    def connect(self, other: DataStream | ConnectedStreams) -> ConnectedStreams:
        if hasattr(other, "transformation"):
            new_transformations = self.transformations + [other.transformation]  # type: ignore[attr-defined]
        else:
            new_transformations = self.transformations + other.transformations  # type: ignore[attr-defined]
        return ConnectedStreams(self._environment, new_transformations)

    def comap(
        self,
        function: type[BaseFunction] | Callable,
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
        if callable(function) and not isinstance(function, type):
            raise NotImplementedError(
                "Lambda functions are not supported for comap operations. Please use a class that inherits from BaseCoMapFunction."
            )

        input_stream_count = len(self.transformations)
        if input_stream_count < 2:
            raise ValueError(
                f"CoMap operations require at least 2 input streams, but only {input_stream_count} streams provided."
            )

        if not isinstance(function, type):
            raise TypeError(
                f"CoMap function must be a class, got {type(function).__name__}. Please provide a class that inherits from BaseCoMapFunction."
            )

        if not issubclass(function, BaseCoMapFunction):
            raise TypeError(
                f"Function {function.__name__} must inherit from BaseCoMapFunction. CoMap operations require CoMap function with mapN methods."
            )

        required_methods = [f"map{i}" for i in range(input_stream_count)]
        missing_methods = [name for name in required_methods if not hasattr(function, name)]
        if missing_methods:
            raise TypeError(
                f"CoMap function {function.__name__} is missing required methods: {missing_methods}. For {input_stream_count} input streams, the function must implement: {required_methods}."
            )

        for method_name in required_methods:
            method = getattr(function, method_name)
            if not callable(method):
                raise TypeError(
                    f"CoMap function {function.__name__}.{method_name} must be callable. Found {type(method).__name__} instead."
                )

        actual_parallelism = parallelism if parallelism is not None else 1
        tr = CoMapTransformation(
            self._environment, function, *args, parallelism=actual_parallelism, **kwargs
        )
        tr.validate_input_streams(input_stream_count)
        return self._apply(tr)

    def join(
        self,
        function: type[BaseJoinFunction] | Callable,
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
        if len(self.transformations) != 2:
            raise ValueError(
                f"Join requires exactly 2 input streams, got {len(self.transformations)}"
            )

        if not isinstance(function, type) or not issubclass(function, BaseJoinFunction):
            raise TypeError("Join function must inherit from BaseJoinFunction")

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
        if callable(key_selector) and not isinstance(key_selector, type):
            raise NotImplementedError(
                "Lambda functions are not supported for keyby operations. Please use KeyByFunction classes."
            )

        from .datastream import DataStream

        input_stream_count = len(self.transformations)
        keyed_transformations = []

        if isinstance(key_selector, list):
            if len(key_selector) != input_stream_count:
                raise ValueError(
                    f"Key selector count ({len(key_selector)}) must match stream count ({input_stream_count})"
                )

            for transformation, selector in zip(self.transformations, key_selector, strict=False):
                individual_stream: DataStream = DataStream(self._environment, transformation)
                keyed_stream = individual_stream.keyby(selector, strategy=strategy)
                keyed_transformations.append(keyed_stream.transformation)
        else:
            for transformation in self.transformations:
                individual_stream = DataStream(self._environment, transformation)
                keyed_stream = individual_stream.keyby(key_selector, strategy=strategy)
                keyed_transformations.append(keyed_stream.transformation)

        return ConnectedStreams(self._environment, keyed_transformations)

    def _apply(self, tr: BaseTransformation) -> DataStream:
        from .datastream import DataStream

        for input_index, upstream_trans in enumerate(self.transformations):
            tr.add_upstream(upstream_trans, input_index=input_index)

        self._environment.pipeline.append(tr)
        return DataStream(self._environment, tr)
