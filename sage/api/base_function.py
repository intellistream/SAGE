from abc import ABC, abstractmethod
from sage.api.collector import Collector



class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """

    def __init__(self):
        self.runtime_context = None  # 需要在compiler里面实例化。
        self.logger=None
        pass

    def insert_collector(self, collector):
        """
        Insert a collector into the function for data collection.

        :param collector: The collector instance to be inserted.
        """
        self.collector:Collector = collector
        self.collector.logger = self.logger
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


class MemoryFunction(BaseFunction):
    def __init__(self):
        self.runtime_context = None  # 需要在compiler里面实例化。
        self.memory= self.runtime_context.memory
        pass

class StatefulFunction(BaseFunction):
    def __init__(self):
        self.runtime_context = None  # 需要在compiler里面实例化。
        self.state = None
        pass


class MemoryFunction(BaseFunction):
    def __init__(self):
        self.runtime_context = None  # 需要在compiler里面实例化。
        self.memory= self.runtime_context.memory
        pass

class StatefulFunction(BaseFunction):
    def __init__(self):
        self.runtime_context = None  # 需要在compiler里面实例化。
        self.state
        pass