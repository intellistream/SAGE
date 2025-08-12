import os
from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union
if TYPE_CHECKING:
    from sage.kernel import TaskContext
import logging


# 构造来源于sage.kernels.runtime/operator/factory.py
class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """
    def __init__(self, *args, **kwargs):
        self.ctx: 'TaskContext' = None # 运行时注入
        self._logger = None
        # 服务代理缓存已移至ServiceCallMixin处理

    @property
    def logger(self):
        if not hasattr(self, "_logger") or self._logger is None:
            if self.ctx is None:
                self._logger = logging.getLogger("")
            else:
                self._logger = self.ctx.logger
        return self._logger
    
    @property
    def name(self):
        if self.ctx is None:
            return self.__class__.__name__
        return self.ctx.name
    
    @property
    def call_service(self):
        """
        同步服务调用语法糖
        
        用法:
            result = self.call_service["cache_service"].get("key1")
            data = self.call_service["db_service"].query("SELECT * FROM users")
        """
        if self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")
        
        return self.ctx.call_service()
    
    @property 
    def call_service_async(self):
        """
        异步服务调用语法糖
        
        用法:
            future = self.call_service_async["cache_service"].get("key1")
            result = future.result()  # 阻塞等待结果
            
            # 或者非阻塞检查
            if future.done():
                result = future.result()
        """
        if self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")
        
        return self.ctx.call_service_async()

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


# class StatefulFunction(BaseFunction):
#     """
#     有状态算子基类：自动在 init 恢复状态，
#     并可通过 save_state() 持久化。
#     """
#     # 子类可覆盖：只保存 include 中字段
#     __state_include__ = []
#     # 默认排除 logger、私有属性和 runtime_context
#     __state_exclude__ = ['logger', '_logger', 'ctx']

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         # 注入上下文
#         # 恢复上次 checkpoint
#         chkpt_dir = os.path.join(self.ctx.env_base_dir, ".sage_checkpoints")
#         chkpt_path = os.path.join(chkpt_dir, f"{self.ctx.name}.chkpt")
#         load_function_state(self, chkpt_path)

#     def save_state(self):
#         """
#         将当前对象状态持久化到 disk，
#         """
#         base = os.path.join(self.ctx.env_base_dir, ".sage_checkpoints")
#         os.makedirs(base, exist_ok=True)
#         path = os.path.join(base, f"{self.ctx.name}.chkpt")
#         save_function_state(self, path)
