from sage_core.api.tuple import Data
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from typing import Tuple, List, Union, Type, Any


class Merger(BaseFunction):
    """
    Splitter function to split a tuple into multiple outputs.
    This is useful for splitting data into multiple streams.
    """

    def __init__(self, config: dict = None, *, session_folder: str = None, **kwargs):
        self.logger = CustomLogger(
            object_name=f"Merger_Function",
            log_level="DEBUG",
            session_folder=session_folder,
            console_output=False,
            file_output=True
        )
        # self.config = config

    @classmethod
    def declare_inputs(cls) -> List[Tuple[str, Type]]:
        """
        Declare the inputs for the function.

        :return: A list of tuples where each tuple contains the input name and its type.
        """
        return [("input1", Any), ("input2", Any), ("input3", Any)]
    


    def execute(self, tag:str,  data: Data[Tuple[str, str]]):
        self.logger.debug(f"Received data for tag '{tag}': {data.data}")
        self.collector.collect(None, data)
            