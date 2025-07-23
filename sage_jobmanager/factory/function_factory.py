from typing import Type, Any, Tuple,TYPE_CHECKING, Union
from sage_core.function.base_function import BaseFunction
if TYPE_CHECKING:
    from ray.actor import ActorHandle
    from sage_runtime.runtime_context import RuntimeContext
    
class FunctionFactory:
    # 由transformation初始化
    def __init__(
        self,
        function_class: Type[BaseFunction],
        function_args: Tuple[Any, ...] = (),
        function_kwargs: dict = None,
    ):
        self.function_class = function_class
        self.function_args = function_args
        self.function_kwargs = function_kwargs or {}
    
    def create_function(self, name:str, ctx:'RuntimeContext') -> BaseFunction:
        """创建函数实例"""
        print(self.function_args)
        print(self.function_kwargs)
        # self.function_kwargs["ctx"] = 
        function = self.function_class(
            *self.function_args, 
            **self.function_kwargs
        )
        function.ctx = ctx
        return function
    
    def __repr__(self) -> str:
        return f"<FunctionFactory {self.function_class.__name__}>"