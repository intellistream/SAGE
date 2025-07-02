from abc import ABC, abstractmethod


class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """

    def __init__(self):
        self.runtime_context;  # 需要在compiler里面实例化。
        pass

    @abstractmethod
    def close(self, *args, **kwargs):
        """
        Abstract method to be implemented by subclasses.

        Each rag must define its own execute logic that processes input data
        and returns the output.

        :param args: Positional input data.
        :param kwargs: Additional keyword arguments.
        :return: Output data.
        """
        pass


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
