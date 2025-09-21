from typing import TYPE_CHECKING, Any, Tuple, Type, Union

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.base_function import BaseFunction

if TYPE_CHECKING:
    from ray.actor import ActorHandle
    from sage.kernel.runtime.context.task_context import TaskContext


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

    def create_function(self, name: str, ctx: "TaskContext") -> BaseFunction:
        """创建函数实例"""
        # logging.info(f"🏭 FunctionFactory.create_function: function_class={self.function_class}, args={self.function_args}, kwargs={self.function_kwargs}")
        if CustomLogger.is_global_console_debug_enabled():
            logging.info(self.function_args)
            logging.info(self.function_kwargs)
        # self.function_kwargs["ctx"] =
        function = self.function_class(*self.function_args, **self.function_kwargs)
        # logging.info(f"🏭 FunctionFactory.create_function: Created function instance: {function}")
        function.ctx = ctx
        return function

    def __repr__(self) -> str:
        function_class_name = getattr(self, "function_class", type(None)).__name__
        return f"<FunctionFactory {function_class_name}>"
