import os
from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union

from dotenv import load_dotenv

from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    from sage_runtime.runtime_context import RuntimeContext

from sage_runtime.state_persistence import load_function_state, save_function_state


# 构造来源于sage_runtime/operator/factory.py
class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """

    def __init__(self, ctx:'RuntimeContext' = None, **kwargs):
        self.runtime_context = ctx
        self.name = ctx.name if ctx else self.__class__.__name__
        self.env_name = ctx.env_name if ctx else None
        self._logger = CustomLogger(
            filename=f"Function_{self.name}",
            env_name= self.env_name,
            console_output="WARNING",
            file_output="DEBUG",
            global_output = "WARNING",
            name = f"{self.name}_{self.__class__.__name__}",
            session_folder=ctx.session_folder if ctx else None
        )
        # self.runtime_context.create_logger()
        self.logger.info(f"Function {self.name} initialized")
        
    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            import logging
            self._logger = logging.getLogger(f"{self.__class__.__name__}")
        return self._logger


    # @abstractmethod
    # def close(self, *args, **kwargs):
    #     """
    #     Abstract method to be implemented by subclasses.

    #     Each rag must define its own execute logic that processes input data
    #     and returns the output.

    #     :param args: Positional input data.
    #     :param kwargs: Additional keyword arguments.
    #     :return: Output data.
    #     """
    #     pass


    @abstractmethod
    def execute(self, data:any):
        """
        Abstract method to be implemented by subclasses.

        Each rag must define its own execute logic that processes input data
        and returns the output.

        :param args: Positional input data.
        :param kwargs: Additional keyword arguments.
        :return: Output data.
        """
        pass





class MemoryFunction(BaseFunction):
    def __init__(self):
        self.runtime_context = None  # 需要在compiler里面实例化。
        self.memory= self.runtime_context.memory
        pass

class StatefulFunction(BaseFunction):
    """
    有状态算子基类：自动在 init 恢复状态，
    并可通过 save_state() 持久化。
    """
    # 子类可覆盖：只保存 include 中字段
    __state_include__ = []
    # 默认排除 logger、私有属性和 runtime_context
    __state_exclude__ = ['logger', '_logger', 'runtime_context']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 注入上下文
        # 恢复上次 checkpoint
        chkpt_dir = os.path.join(self.runtime_context.session_folder, ".sage_checkpoints")
        chkpt_path = os.path.join(chkpt_dir, f"{self.runtime_context.name}.chkpt")
        load_function_state(self, chkpt_path)

    def save_state(self):
        """
        将当前对象状态持久化到 disk，
        """
        base = os.path.join(self.runtime_context.session_folder, ".sage_checkpoints")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{self.runtime_context.name}.chkpt")
        save_function_state(self, path)

# class MemoryFunction(BaseFunction):
#     def __init__(self):
#         self.runtime_context = None  # 需要在compiler里面实例化。

#     @property
#     def memory(self):
#         if self.runtime_context is None:
#             raise RuntimeError("runtime_context is not set")
#         return self.runtime_context.memory

# class StatefulFunction(BaseFunction):
#     def __init__(self):
#         self.runtime_context = None  # 需要在compiler里面实例化。
#         self.state
#         pass
