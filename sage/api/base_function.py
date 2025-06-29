from abc import ABC, abstractmethod
from sage.utils.custom_logger import CustomLogger


class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """

    def __init__(self):
        """
        Initializes the logger for the function instance.
        """
        self.logger = CustomLogger(
            object_name=self.__class__.__name__,
            log_level="DEBUG",
            console_output=True,
            file_output=False  # 可根据需求选择是否输出到文件
        )

    @abstractmethod
    def execute(self, *args, **kwargs):
        """
        Abstract method to be implemented by subclasses.

        Each function must define its own execute logic that processes input data
        and returns the output.

        :param args: Positional input data.
        :param kwargs: Additional keyword arguments.
        :return: Output data.
        """
        pass
