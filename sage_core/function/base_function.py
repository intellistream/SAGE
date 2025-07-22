import os
from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union
if TYPE_CHECKING:
    from sage_runtime.runtime_context import RuntimeContext

from sage_utils.state_persistence import load_function_state, save_function_state


# 构造来源于sage_runtime/operator/factory.py
class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """

    def __init__(self, ctx:'RuntimeContext' = None, **kwargs):
        self.ctx = ctx
        # self.runtime_context.create_logger()
        self.logger.info(f"Function {self.name} initialized")
        
    @property
    def logger(self):
        return self.ctx.logger
    
    @property
    def name(self):
        return self.ctx.name

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
        chkpt_dir = os.path.join(self.ctx.env_base_dir, ".sage_checkpoints")
        chkpt_path = os.path.join(chkpt_dir, f"{self.ctx.name}.chkpt")
        load_function_state(self, chkpt_path)

    def save_state(self):
        """
        将当前对象状态持久化到 disk，
        """
        base = os.path.join(self.ctx.env_base_dir, ".sage_checkpoints")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{self.ctx.name}.chkpt")
        save_function_state(self, path)