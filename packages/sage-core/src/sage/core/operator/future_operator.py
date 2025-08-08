from __future__ import annotations
from typing import Any, List
from .base_operator import BaseOperator
from sage.core.factory.function_factory import FunctionFactory


class FutureOperator(BaseOperator):
    """
    Future transformation的占位符operator。
    这个operator不会被实际执行，只是作为placeholder存在。
    """
    
    def __init__(self, function_factory: FunctionFactory, basename: str, env_name: str):
        super().__init__(function_factory, basename, env_name)
        self.is_future = True
    
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
