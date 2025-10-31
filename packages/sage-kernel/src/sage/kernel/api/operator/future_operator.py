from __future__ import annotations

from typing import Any

from sage.kernel.runtime.factory.function_factory import FunctionFactory

from .base_operator import BaseOperator


class FutureOperator(BaseOperator):
    """
    Future transformation的占位符operator。
    这个operator不会被实际执行，只是作为placeholder存在。
    """

    def __init__(self, function_factory: FunctionFactory, ctx, env_name: str = ""):
        super().__init__(function_factory, ctx)  # type: ignore
        self.is_future = True
        self.basename = getattr(ctx, "name", env_name)

    def process(self, data: Any) -> Any:
        """
        Future operator不应该被直接调用
        """
        raise RuntimeError("FutureOperator should not be called directly. It's a placeholder.")

    def emit(self, result: Any) -> None:
        """
        Future operator不应该被直接调用
        """
        raise RuntimeError("FutureOperator should not be called directly. It's a placeholder.")

    def __repr__(self) -> str:
        return f"FutureOperator({self.basename}, placeholder)"
