from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, get_args, get_origin

from sage.foundation import BaseFunction, CustomLogger, PrintSink, wrap_lambda

from ._kernel_bindings import (
    BaseTransformation,
    FilterTransformation,
    FlatMapTransformation,
    FutureTransformation,
    KeyByTransformation,
    MapTransformation,
    SinkTransformation,
    SourceTransformation,
)
from .connected_streams import ConnectedStreams

if TYPE_CHECKING:
    from sage.runtime.base_environment import BaseEnvironment

T = TypeVar("T")


class DataStream(Generic[T]):
    """Main-repo owned stream abstraction."""

    def __init__(self, env: BaseEnvironment, transformation: BaseTransformation):
        self.logger = CustomLogger()
        self._environment = env
        self.transformation = transformation
        self._type_param = self._resolve_type_param()

        self.logger.debug(
            f"DataStream created with transformation: {transformation.function_class.__name__}, type_param: {self._type_param}"
        )

    def _get_transformation_classes(self):
        if not hasattr(self, "_transformation_classes"):
            self._transformation_classes = {
                "BaseTransformation": BaseTransformation,
                "FilterTransformation": FilterTransformation,
                "FlatMapTransformation": FlatMapTransformation,
                "MapTransformation": MapTransformation,
                "SinkTransformation": SinkTransformation,
                "SourceTransformation": SourceTransformation,
                "KeyByTransformation": KeyByTransformation,
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

    def filter(
        self,
        function: type[BaseFunction] | Callable,
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, "filter")

        actual_parallelism = parallelism if parallelism is not None else 1
        FilterTransformation = self._get_transformation_classes()["FilterTransformation"]
        tr = FilterTransformation(
            self._environment, function, *args, parallelism=actual_parallelism, **kwargs
        )
        return self._apply(tr)

    def flatmap(
        self,
        function: type[BaseFunction] | Callable,
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, "flatmap")

        actual_parallelism = parallelism if parallelism is not None else 1
        FlatMapTransformation = self._get_transformation_classes()["FlatMapTransformation"]
        tr = FlatMapTransformation(
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
        self._apply(tr)
        return self

    def keyby(
        self,
        function: type[BaseFunction] | Callable,
        strategy: str = "hash",
        *args,
        parallelism: int | None = None,
        **kwargs,
    ) -> DataStream:
        if callable(function) and not isinstance(function, type):
            function = wrap_lambda(function, "keyby")

        actual_parallelism = parallelism if parallelism is not None else 1
        KeyByTransformation = self._get_transformation_classes()["KeyByTransformation"]
        tr = KeyByTransformation(
            self._environment,
            function,
            strategy=strategy,
            *args,
            parallelism=actual_parallelism,
            **kwargs,
        )
        return self._apply(tr)

    def connect(self, other: DataStream | ConnectedStreams) -> ConnectedStreams:
        if isinstance(other, DataStream):
            return ConnectedStreams(self._environment, [self.transformation, other.transformation])
        new_transformations = [self.transformation] + other.transformations
        return ConnectedStreams(self._environment, new_transformations)

    def fill_future(self, future_stream: DataStream) -> None:
        if not isinstance(future_stream.transformation, FutureTransformation):
            raise ValueError("Target stream must be a future stream created by env.from_future()")

        future_trans = future_stream.transformation
        if future_trans.filled:
            raise RuntimeError(
                f"Future stream '{future_trans.future_name}' has already been filled"
            )

        future_trans.fill_with_transformation(self.transformation)

        self.logger.debug(
            f"Filled future stream '{future_trans.future_name}' with transformation '{self.transformation.basename}'"
        )
        self.logger.info(
            f"Created feedback edge: {self.transformation.basename} -> {future_trans.future_name}"
        )

    def print(self, prefix: str = "", separator: str = " | ", colored: bool = True) -> DataStream:
        return self.sink(PrintSink, prefix=prefix, separator=separator, colored=colored)

    def _apply(self, tr: BaseTransformation) -> DataStream:
        tr.add_upstream(self.transformation, input_index=0)
        self._environment.pipeline.append(tr)
        return DataStream(self._environment, tr)

    def _resolve_type_param(self):
        orig = getattr(self, "__orig_class__", None)
        if orig and get_origin(orig) == DataStream:
            return get_args(orig)[0]
        return Any
