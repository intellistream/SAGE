from typing import Type, Any, Tuple
from sage_core.api.base_function import BaseFunction

class FunctionFactory:
    # 由transformation初始化
    def __init__(
        self,
        function_class: Type[BaseFunction],
        function_args: Tuple[Any, ...] = (),
        function_kwargs: dict = None
    ):
        self.function_class = function_class
        self.function_args = function_args
        self.function_kwargs = function_kwargs or {}
    
    def create_function(self, **additional_kwargs) -> BaseFunction:
        """创建函数实例"""
        # 合并原有的 kwargs 和额外的 kwargs
        merged_kwargs = {**self.function_kwargs, **additional_kwargs}
        return self.function_class(*self.function_args, **merged_kwargs)
    
    def __repr__(self) -> str:
        return f"<FunctionFactory {self.function_class.__name__}>"