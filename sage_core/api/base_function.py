import os
from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union

from dotenv import load_dotenv

from sage_core.api.collector import Collector
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    from sage_runtime.operator.runtime_context import RuntimeContext



# 构造来源于sage_runtime/operator/factory.py
class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """

    def __init__(self, session_folder:str = None, name:str = None, env_name:str = None,  **kwargs):
        # TODO: api_key应该是由env来提供和解析的吧？
        self.api_key = None
        self.runtime_context:RuntimeContext  # 需要在compiler里面实例化。
        name = name or self.__class__.__name__
        self.logger = CustomLogger(
            filename=f"Fuction_{name}",
            env_name=env_name,
            session_folder=session_folder,
            console_output=False,
            file_output=True,
            global_output = True,
            name = f"{name}_Function"
        )
        
        self.get_key()

    def get_key(self):
        # finds and loads .env into os.environ
        load_dotenv()
        # TODO: add an iteration to find the suitable key for the url that the user configured.
        if not os.getenv("ALIBABA_API_KEY"):
            raise RuntimeError("Missing ALIBABA_API_KEY in environment or .env file")
        else:
            self.api_key = os.getenv("ALIBABA_API_KEY")
        pass




    # TODO: 创建一个function factory，并把对应的逻辑封装进去
    def insert_runtime_context(self, runtime_context):
        """
        Insert a runtime_tests context into the function for accessing runtime_tests data.
        :param runtime_context: The runtime_tests context instance to be inserted.
        """
        self.runtime_context = runtime_context

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