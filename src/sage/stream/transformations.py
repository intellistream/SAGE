"""Main-repo owned transformation layer for SAGE streams."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from sage.foundation import BaseJoinFunction, CustomLogger, FutureFunction

from ._kernel_runtime import (
    BatchOperator,
    CoMapOperator,
    FilterOperator,
    FlatMapOperator,
    FunctionFactory,
    FutureOperator,
    JoinOperator,
    KeyByOperator,
    MapOperator,
    OperatorFactory,
    SinkOperator,
    SourceOperator,
)

if TYPE_CHECKING:
    from sage.foundation import BaseCoMapFunction, BaseFunction
    from sage.runtime.base_environment import BaseEnvironment


__all__ = [
    "BaseTransformation",
    "SourceTransformation",
    "BatchTransformation",
    "MapTransformation",
    "FilterTransformation",
    "FlatMapTransformation",
    "SinkTransformation",
    "KeyByTransformation",
    "JoinTransformation",
    "CoMapTransformation",
    "FutureTransformation",
]


def is_abstract_method(method: Any) -> bool:
    return getattr(method, "__isabstractmethod__", False)


def validate_required_methods(
    cls: type,
    required_methods: list[str],
    class_name: str | None = None,
) -> None:
    display_name = class_name or cls.__name__
    missing = []
    for method_name in required_methods:
        if not hasattr(cls, method_name) or is_abstract_method(getattr(cls, method_name)):
            missing.append(method_name)
    if missing:
        raise ValueError(f"{display_name} must implement required methods: {', '.join(missing)}")


class BaseTransformation:
    def __init__(
        self,
        env: BaseEnvironment,
        function: type[BaseFunction],
        *args,
        name: str | None = None,
        parallelism: int = 1,
        **kwargs,
    ) -> None:
        self.operator_class: type
        self.remote = env.platform == "remote"
        self.env_name = env.name
        self.env = env
        self.function_class = function
        self.function_args = args
        self.function_kwargs = kwargs
        self.basename = name or self.function_class.__name__

        existing_names = [t.basename for t in env.pipeline if hasattr(t, "basename")]
        original_basename = self.basename
        counter = 0
        while self.basename in existing_names:
            counter += 1
            self.basename = f"{original_basename}_{counter}"

        self.logger = CustomLogger()
        self.upstreams: list[BaseTransformation] = []
        self.downstreams: dict[str, int] = {}
        self.parallelism = parallelism
        self._operator_factory: OperatorFactory | None = None
        self._function_factory: FunctionFactory | None = None

    def add_upstream(self, upstream_trans: BaseTransformation, input_index: int = 0) -> None:
        self.upstreams.append(upstream_trans)
        upstream_trans.downstreams[self.basename] = input_index

    @property
    def function_factory(self) -> FunctionFactory:
        if self._function_factory is None:
            self._function_factory = FunctionFactory(
                function_class=self.function_class,
                function_args=self.function_args,
                function_kwargs=self.function_kwargs,
            )
        return self._function_factory

    def get_operator_kwargs(self) -> dict[str, Any]:
        return {}

    @property
    def operator_factory(self) -> OperatorFactory:
        if self._operator_factory is None:
            self._operator_factory = OperatorFactory(
                operator_class=self.operator_class,
                function_factory=self.function_factory,
                basename=self.basename,
                env_name=self.env_name,
                remote=self.remote,
                **self.get_operator_kwargs(),
            )
        return self._operator_factory

    @property
    def delay(self) -> float:
        return 0.1

    @property
    def is_spout(self) -> bool:
        return False

    @property
    def is_sink(self) -> bool:
        return False

    @property
    def is_merge_operation(self) -> bool:
        return not hasattr(self.function_class, "is_comap") or not getattr(
            self.function_class, "is_comap", False
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.function_class.__name__} at {hex(id(self))}>"


class SourceTransformation(BaseTransformation):
    def __init__(
        self,
        env: BaseEnvironment,
        function: type[BaseFunction],
        *args,
        delay: float = 1.0,
        **kwargs,
    ) -> None:
        self.operator_class = SourceOperator
        self._delay = delay
        super().__init__(env, function, *args, **kwargs)

    @property
    def delay(self) -> float:
        return self._delay

    @property
    def is_spout(self) -> bool:
        return True


class BatchTransformation(BaseTransformation):
    def __init__(
        self,
        env: BaseEnvironment,
        function: type[BaseFunction],
        *args,
        delay: float = 0.1,
        progress_log_interval: int = 100,
        **kwargs,
    ) -> None:
        self.operator_class = BatchOperator
        self._delay = delay
        self._progress_log_interval = progress_log_interval
        super().__init__(env, function, *args, **kwargs)

    @property
    def delay(self) -> float:
        return self._delay

    @property
    def progress_log_interval(self) -> int:
        return self._progress_log_interval

    @property
    def is_spout(self) -> bool:
        return True

    def get_operator_kwargs(self) -> dict[str, Any]:
        return {"progress_log_interval": self._progress_log_interval}


class MapTransformation(BaseTransformation):
    def __init__(self, env: BaseEnvironment, function: type[BaseFunction], *args, **kwargs) -> None:
        self.operator_class = MapOperator
        super().__init__(env, function, *args, **kwargs)


class FilterTransformation(BaseTransformation):
    def __init__(self, env: BaseEnvironment, function: type[BaseFunction], *args, **kwargs) -> None:
        self.operator_class = FilterOperator
        super().__init__(env, function, *args, **kwargs)


class FlatMapTransformation(BaseTransformation):
    def __init__(self, env: BaseEnvironment, function: type[BaseFunction], *args, **kwargs) -> None:
        self.operator_class = FlatMapOperator
        super().__init__(env, function, *args, **kwargs)


class SinkTransformation(BaseTransformation):
    def __init__(
        self,
        env: BaseEnvironment,
        function: type[BaseFunction],
        *args,
        batch_size: int = 1,
        **kwargs,
    ) -> None:
        self.operator_class = SinkOperator
        self.batch_size = batch_size
        super().__init__(env, function, *args, **kwargs)

    @property
    def is_sink(self) -> bool:
        return True


class KeyByTransformation(BaseTransformation):
    def __init__(
        self,
        env: BaseEnvironment,
        key_selector_function: type[BaseFunction],
        strategy: str = "hash",
        name: str | None = None,
        parallelism: int = 1,
        *args,
        **kwargs,
    ) -> None:
        self.operator_class = KeyByOperator
        self.partition_strategy = strategy
        super().__init__(
            env,
            key_selector_function,
            *args,
            name=name,
            parallelism=parallelism,
            **kwargs,
        )

    def get_operator_kwargs(self) -> dict[str, Any]:
        return {"partition_strategy": self.partition_strategy}


class JoinTransformation(BaseTransformation):
    def __init__(
        self, env: BaseEnvironment, function: type[BaseJoinFunction], *args, **kwargs
    ) -> None:
        if not hasattr(function, "is_join") or not function.is_join:
            raise ValueError(
                f"Function {function.__name__} is not a Join function. "
                "Join functions must inherit from BaseJoinFunction and have is_join=True."
            )
        validate_required_methods(
            function, ["execute"], class_name=f"Join function {function.__name__}"
        )
        self._validate_execute_signature(function)
        self.operator_class = JoinOperator
        super().__init__(env, function, *args, **kwargs)

    def _validate_execute_signature(self, function_class: type[BaseJoinFunction]) -> None:
        try:
            params = list(inspect.signature(function_class.execute).parameters.keys())
            expected = ["self", "payload", "key", "tag"]
            if len(params) < len(expected):
                raise ValueError(
                    f"Join function {function_class.__name__}.execute() must accept parameters: {', '.join(expected[1:])}. Got: {', '.join(params[1:])}"
                )
        except Exception as exc:
            self.logger.warning(f"Could not validate execute method signature: {exc}")

    @property
    def supported_input_count(self) -> int:
        return 2

    @property
    def max_supported_streams(self) -> int:
        return 2

    def validate_input_streams(self, input_count: int) -> None:
        if input_count != self.supported_input_count:
            raise ValueError(
                f"Join function {self.function_class.__name__} requires exactly {self.supported_input_count} input streams, but {input_count} streams provided."
            )
        if input_count < 2:
            raise ValueError("Join transformation requires at least 2 input streams.")

    def validate_keyed_streams(self, stream_transformations: list[BaseTransformation]) -> None:
        for i, transformation in enumerate(stream_transformations):
            if not self._is_keyed_stream(transformation):
                raise ValueError(
                    f"Join requires all input streams to be keyed. Stream {i} ({transformation.function_class.__name__}) is not keyed. Use .keyby() before .join()."
                )

    def _is_keyed_stream(self, transformation: BaseTransformation) -> bool:
        if isinstance(transformation, KeyByTransformation):
            return True

        current = transformation
        visited = set()
        while current and id(current) not in visited:
            visited.add(id(current))
            if isinstance(current, KeyByTransformation):
                return True
            if current.upstreams:
                if len(current.upstreams) == 1:
                    current = current.upstreams[0]
                else:
                    return all(self._is_keyed_stream(upstream) for upstream in current.upstreams)
            else:
                break
        return False

    @property
    def is_merge_operation(self) -> bool:
        return False


class CoMapTransformation(BaseTransformation):
    def __init__(
        self, env: BaseEnvironment, function: type[BaseCoMapFunction], *args, **kwargs
    ) -> None:
        if not hasattr(function, "is_comap") or not function.is_comap:
            raise ValueError(
                f"Function {function.__name__} is not a CoMap function. "
                "CoMap functions must inherit from BaseCoMapFunction and have is_comap=True."
            )
        validate_required_methods(
            function, ["map0", "map1"], class_name=f"CoMap function {function.__name__}"
        )
        self.operator_class = CoMapOperator
        super().__init__(env, function, *args, **kwargs)

    @property
    def supported_input_count(self) -> int:
        count = 0
        method_index = 0
        while True:
            method_name = f"map{method_index}"
            if not hasattr(self.function_class, method_name):
                break
            method = getattr(self.function_class, method_name)
            if is_abstract_method(method):
                break
            count += 1
            method_index += 1
        return count

    def validate_input_streams(self, input_count: int) -> None:
        supported_count = self.supported_input_count
        if input_count > supported_count:
            raise ValueError(
                f"CoMap function {self.function_class.__name__} supports maximum {supported_count} input streams, but {input_count} provided."
            )
        if input_count < 2:
            raise ValueError("CoMap transformation requires at least 2 input streams.")


class FutureTransformation(BaseTransformation):
    def __init__(self, env: BaseEnvironment, name: str) -> None:
        self.operator_class = FutureOperator
        super().__init__(env=env, function=FutureFunction, name=name, parallelism=1)
        self.is_future = True
        self.filled = False
        self.actual_transformation: BaseTransformation | None = None
        self.future_name = name

    def fill_with_transformation(self, actual_transformation: BaseTransformation) -> None:
        if self.filled:
            raise RuntimeError(
                f"Future transformation '{self.future_name}' has already been filled"
            )
        self.actual_transformation = actual_transformation
        self.filled = True
        self._redirect_downstreams()

    def _redirect_downstreams(self) -> None:
        if not self.actual_transformation:
            return
        for downstream_name, input_index in self.downstreams.items():
            downstream_trans = self._find_transformation_by_name(downstream_name)
            if downstream_trans and self.actual_transformation:
                if self in downstream_trans.upstreams:
                    downstream_trans.upstreams.remove(self)
                downstream_trans.upstreams.append(self.actual_transformation)
                self.actual_transformation.downstreams[downstream_name] = input_index
        self.downstreams.clear()

    def _find_transformation_by_name(self, name: str) -> BaseTransformation | None:
        for trans in self.env.pipeline:
            if trans.basename == name:
                return trans
        return None

    def __repr__(self) -> str:
        status = "filled" if self.filled else "unfilled"
        actual = (
            f" -> {self.actual_transformation.basename}"
            if self.filled and self.actual_transformation
            else ""
        )
        return f"FutureTransformation({self.future_name}, {status}{actual})"
