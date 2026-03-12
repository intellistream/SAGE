"""Core function contracts reclaimed into the main SAGE repository.

This module intentionally provides the small subset of common-layer primitives
that the in-tree stream/runtime surface depends on directly.
"""

from __future__ import annotations

import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Hashable
from typing import Any


class BaseFunction(ABC):
    """Minimal base class for user-defined stream/runtime functions."""

    __state_include__: list[str] = []
    __state_exclude__: list[str] = ["ctx", "_logger", "logger"]

    def __init__(self, *args, **kwargs) -> None:
        self.ctx: Any | None = None
        self._logger: logging.Logger | None = None

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            if self.ctx is not None and hasattr(self.ctx, "logger"):
                self._logger = self.ctx.logger
            else:
                self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger

    @property
    def name(self) -> str:
        if self.ctx is not None and hasattr(self.ctx, "name"):
            return str(self.ctx.name)
        return self.__class__.__name__

    def call_service(
        self,
        service_name: str,
        *args,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs,
    ) -> Any:
        if self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")
        return self.ctx.call_service(service_name, *args, timeout=timeout, method=method, **kwargs)

    def call_service_async(
        self,
        service_name: str,
        *args,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs,
    ) -> Any:
        if self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")
        return self.ctx.call_service_async(
            service_name,
            *args,
            timeout=timeout,
            method=method,
            **kwargs,
        )

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the function body."""


class MapFunction(BaseFunction):
    @abstractmethod
    def execute(self, data: Any) -> Any:
        pass


class FilterFunction(BaseFunction):
    @abstractmethod
    def execute(self, data: Any) -> bool:
        pass


class FlatMapFunction(BaseFunction):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.out: Collector | None = None

    def insert_collector(self, collector: Collector) -> None:
        self.out = collector
        self.out.logger = self.logger

    def collect(self, data: Any) -> None:
        if self.out is None:
            raise RuntimeError("Collector not initialized. This should be set by the runtime.")
        self.out.collect(data)

    @abstractmethod
    def execute(self, data: Any) -> list[Any]:
        pass


class SinkFunction(BaseFunction):
    @abstractmethod
    def execute(self, data: Any) -> None:
        pass


class SourceFunction(BaseFunction):
    @abstractmethod
    def execute(self) -> Any:
        pass


class BatchFunction(BaseFunction):
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        pass


class KeyByFunction(BaseFunction):
    @abstractmethod
    def execute(self, data: Any) -> Hashable:
        pass


class BaseJoinFunction(BaseFunction):
    @property
    def is_join(self) -> bool:
        return True

    @abstractmethod
    def execute(self, payload: Any, key: Any, tag: int) -> list[Any]:
        pass


class BaseCoMapFunction(BaseFunction):
    """Base class for multi-stream co-map functions."""

    is_comap = True


class FutureFunction(BaseFunction):
    def __call__(self, *args, **kwargs) -> Any:
        raise RuntimeError("FutureFunction should not be called directly. It's a placeholder.")

    def call(self, data: Any) -> Any:
        raise RuntimeError("FutureFunction should not be called directly. It's a placeholder.")

    def execute(self, *args, **kwargs) -> Any:
        raise RuntimeError("FutureFunction should not be executed directly.")

    def __repr__(self) -> str:
        return "FutureFunction(placeholder)"


class Collector:
    """Tiny collector used by flatmap-style functions."""

    def __init__(self, logger: Any | None = None) -> None:
        self.items: list[Any] = []
        self.logger: Any | None = logger

    def collect(self, item: Any) -> None:
        self.items.append(item)
        if self.logger is not None:
            self.logger.debug(f"Collected item: {item}")

    def get_collected_data(self) -> list[Any]:
        return self.items.copy()

    def clear(self) -> None:
        self.items.clear()


class LambdaMapFunction(MapFunction):
    def __init__(self, lambda_func: Callable[[Any], Any], **kwargs) -> None:
        super().__init__(**kwargs)
        self.lambda_func = lambda_func

    def execute(self, data: Any) -> Any:
        return self.lambda_func(data)


class LambdaFilterFunction(FilterFunction):
    def __init__(self, lambda_func: Callable[[Any], bool], **kwargs) -> None:
        super().__init__(**kwargs)
        self.lambda_func = lambda_func

    def execute(self, data: Any) -> bool:
        return bool(self.lambda_func(data))


class LambdaFlatMapFunction(FlatMapFunction):
    def __init__(self, lambda_func: Callable[[Any], list[Any]], **kwargs) -> None:
        super().__init__(**kwargs)
        self.lambda_func = lambda_func

    def execute(self, data: Any) -> list[Any]:
        result = self.lambda_func(data)
        if not isinstance(result, list):
            raise TypeError(f"FlatMap lambda function must return a list, got {type(result)}")
        return result


class LambdaSinkFunction(SinkFunction):
    def __init__(self, lambda_func: Callable[[Any], None], **kwargs) -> None:
        super().__init__(**kwargs)
        self.lambda_func = lambda_func

    def execute(self, data: Any) -> None:
        self.lambda_func(data)


class LambdaSourceFunction(SourceFunction):
    def __init__(self, lambda_func: Callable[[], Any], **kwargs) -> None:
        super().__init__(**kwargs)
        self.lambda_func = lambda_func

    def execute(self) -> Any:
        return self.lambda_func()


class LambdaKeyByFunction(KeyByFunction):
    def __init__(self, lambda_func: Callable[[Any], Hashable], **kwargs) -> None:
        super().__init__(**kwargs)
        self.lambda_func = lambda_func

    def execute(self, data: Any) -> Hashable:
        return self.lambda_func(data)


def detect_lambda_type(func: Callable) -> str:
    """Infer a lambda wrapper type from signature/annotation."""
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        return_annotation = sig.return_annotation

        if len(params) == 0:
            return "source"
        if len(params) != 1:
            raise ValueError(f"Lambda function must have 0 or 1 parameter, got {len(params)}")
        if return_annotation is bool:
            return "filter"
        if getattr(return_annotation, "__origin__", None) is list:
            return "flatmap"
        if return_annotation in (type(None), None):
            return "sink"
        return "map"
    except Exception:
        return "map"


def wrap_lambda(func: Callable, func_type: str | None = None) -> type[BaseFunction]:
    """Wrap a lambda/callable into a function class compatible with runtime operators."""
    resolved_type = func_type or detect_lambda_type(func)

    if resolved_type == "map":

        class WrappedMapFunction(LambdaMapFunction):
            def __init__(self, **kwargs) -> None:
                super().__init__(func, **kwargs)

        return WrappedMapFunction

    if resolved_type == "filter":

        class WrappedFilterFunction(LambdaFilterFunction):
            def __init__(self, **kwargs) -> None:
                super().__init__(func, **kwargs)

        return WrappedFilterFunction

    if resolved_type == "flatmap":

        class WrappedFlatMapFunction(LambdaFlatMapFunction):
            def __init__(self, **kwargs) -> None:
                super().__init__(func, **kwargs)

        return WrappedFlatMapFunction

    if resolved_type == "sink":

        class WrappedSinkFunction(LambdaSinkFunction):
            def __init__(self, **kwargs) -> None:
                super().__init__(func, **kwargs)

        return WrappedSinkFunction

    if resolved_type == "source":

        class WrappedSourceFunction(LambdaSourceFunction):
            def __init__(self, **kwargs) -> None:
                super().__init__(func, **kwargs)

        return WrappedSourceFunction

    if resolved_type == "keyby":

        class WrappedKeyByFunction(LambdaKeyByFunction):
            def __init__(self, **kwargs) -> None:
                super().__init__(func, **kwargs)

        return WrappedKeyByFunction

    raise ValueError(f"Unsupported function type: {resolved_type}")


__all__ = [
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "FlatMapFunction",
    "SinkFunction",
    "SourceFunction",
    "BatchFunction",
    "KeyByFunction",
    "BaseJoinFunction",
    "BaseCoMapFunction",
    "Collector",
    "FutureFunction",
    "wrap_lambda",
]
