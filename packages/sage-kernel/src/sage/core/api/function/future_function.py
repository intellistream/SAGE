from __future__ import annotations
from typing import Any, Iterator
from .base_function import BaseFunction


class FutureFunction(BaseFunction):
    """
    Future transformation的占位符函数。
    这个函数不会被实际执行，只是作为placeholder存在。
    """

    
    def __call__(self, *args, **kwargs) -> Any:
        """
        Future function不应该被直接调用
        """
        raise RuntimeError("FutureFunction should not be called directly. It's a placeholder.")
    
    def call(self, data: Any) -> Any:
        """
        Future function不应该被直接调用
        """
        raise RuntimeError("FutureFunction should not be called directly. It's a placeholder.")
    
    def __repr__(self) -> str:
        return "FutureFunction(placeholder)"
