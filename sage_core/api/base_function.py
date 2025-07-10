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
        self.api_key = None
        self.runtime_context:RuntimeContext  # 需要在compiler里面实例化。
        name = name or self.__class__.__name__
        self.logger = CustomLogger(
            filename=f"Fuction_{name}",
            env_name=env_name,
            session_folder=session_folder,
            console_output=True,
            file_output=False,
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

    @classmethod # 多路输出的function可以override这个方法
    def declare_outputs(cls) -> List[Tuple[str, Type]]:
        return [("default", Any)]

    @classmethod
    def declare_inputs(cls) -> List[Tuple[str, Type]]:
        """
        Declare the inputs for the function.

        :return: A list of tuples where each tuple contains the input name and its type.
        """
        return [("default", Any)]

    @classmethod
    def get_output_num(cls) -> int:
        return len(cls.declare_outputs())

    @classmethod
    def get_input_num(cls) -> int:
        """
        Get the number of inputs for the function.

        :return: The number of inputs.
        """
        return len(cls.declare_inputs())

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
    def execute(self, *args, **kwargs):
        """
        Abstract method to be implemented by subclasses.

        Each rag must define its own execute logic that processes input data
        and returns the output.

        :param args: Positional input data.
        :param kwargs: Additional keyword arguments.
        :return: Output data.
        """
        pass

    def _extract_data(self, data: Union[Any, Data]) -> Any:
        """
        Extract raw data from Data wrapper or return the data as-is.
        
        Args:
            data: Either raw data or Data wrapper
            
        Returns:
            Any: The extracted raw data
        """
        if isinstance(data, Data):
            return data.data
        return data

    def _wrap_data(self, data: Any) -> Data:
        """
        Wrap raw data into Data wrapper.
        
        Args:
            data: Raw data to wrap
            
        Returns:
            Data: Wrapped data
        """
        if isinstance(data, Data):
            return data
        return Data(data)





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


