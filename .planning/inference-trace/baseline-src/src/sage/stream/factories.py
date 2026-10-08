"""Main-repo owned function/operator factory helpers for stream transformations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sage.foundation import BaseFunction

if TYPE_CHECKING:
    from ._runtime_kernel_types import TaskContext


class FunctionFactory:
    def __init__(
        self,
        function_class: type[BaseFunction],
        function_args: tuple[Any, ...] = (),
        function_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.function_class = function_class
        self.function_args = function_args
        self.function_kwargs = function_kwargs or {}

    def create_function(self, name: str, ctx: TaskContext) -> BaseFunction:
        function = self.function_class(*self.function_args, **self.function_kwargs)
        function.ctx = ctx
        return function

    def __repr__(self) -> str:
        return f"<FunctionFactory {self.function_class.__name__}>"


class OperatorFactory:
    def __init__(
        self,
        operator_class: type[Any],
        function_factory: FunctionFactory,
        env_name: str | None = None,
        remote: bool = False,
        **operator_kwargs: Any,
    ) -> None:
        self.operator_class = operator_class
        self.operator_kwargs = operator_kwargs
        self.function_factory = function_factory
        self.env_name = env_name
        self.remote = remote

    def create_operator(self, runtime_context: TaskContext) -> Any:
        return self.operator_class(
            self.function_factory,
            runtime_context,
            **self.operator_kwargs,
        )
