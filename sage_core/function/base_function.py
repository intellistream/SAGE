import os
from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union

from dotenv import load_dotenv

from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    from sage_runtime.runtime_context import RuntimeContext
    from ray.actor import ActorHandle


# 构造来源于sage_runtime/operator/factory.py
class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """

    def __init__(self, **kwargs):

        # TODO: api_key应该是由env来提供和解析的吧？
        # Issue URL: https://github.com/intellistream/SAGE/issues/145
        self.api_key = None
        self.get_key()

    def runtime_init(self, ctx: 'RuntimeContext') -> None:
        """
        Initialize the function with the runtime context.
        This method should be called after the function is created.
        """
        self.runtime_context = ctx
        self.name = ctx.name
        self.logger = CustomLogger(
            filename=f"Function_{ctx.name}",
            env_name=ctx.env_name,
            console_output="WARNING",
            file_output="DEBUG",
            global_output = "WARNING",
            name = f"{ctx.name}_{self.__class__.__name__}",
            session_folder=ctx.session_folder
        )
        self.runtime_context.create_logger()
        self.logger.info(f"Function {self.name} initialized with runtime context {ctx}")


    def get_key(self):
        # finds and loads .env into os.environ
        load_dotenv()
        # TODO: add an iteration to find the suitable key for the url that the user configured.
        if not os.getenv("ALIBABA_API_KEY"):
            raise RuntimeError("Missing ALIBABA_API_KEY in environment or .env file")
        else:
            self.api_key = os.getenv("ALIBABA_API_KEY")
        pass

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
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.runtime_context = None  # 需要在compiler里面实例化。
        self.state = None
        pass


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




"""
🧾 SAGE 函数通信协议（简洁版 P-NIP-S）
所有 Function.execute() 方法必须接收 一个且仅一个参数。

上游函数返回的结果，完整作为单一对象传递给下游。

不支持自动 unpack、参数猜测、magic 参数绑定。

支持返回：

单值类型（str, dict, MyObject）

结构类型（tuple, dataclass, TypedDict）

建图阶段将根据函数签名与上游类型进行匹配校验（静态分析）。

不匹配时将发出 warning 或在 strict mode 下拒绝绑定。

operator 层不会对 data 进行二次解包或 magic 转换。



"""