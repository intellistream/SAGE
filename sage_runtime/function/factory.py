from typing import Type, Any, Tuple,TYPE_CHECKING, Union
from sage_core.function.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    from ray.actor import ActorHandle

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
    
    def create_function(self, name:str) -> BaseFunction:
        """创建函数实例"""
        return self.function_class(
            *self.function_args, 
            **self.function_kwargs, 
        )
    
    def __repr__(self) -> str:
        return f"<FunctionFactory {self.function_class.__name__}>"