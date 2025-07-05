from sage_core.api.tuple import Data
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from typing import Tuple, List, Union


class Splitter(BaseFunction):
    """
    Splitter function to split a tuple into multiple outputs.
    This is useful for splitting data into multiple streams.
    """

    def __init__(self, config: dict = None, *, session_folder: str = None, **kwargs):
        self.logger = CustomLogger(
            object_name=f"Splitter_Function",
            session_folder=session_folder,
            console_output=False,
            file_output=True
        )
        # self.config = config

    def execute(self, data: Data[Tuple[str, str]]):
        if(data.data[1].find("False") != -1):
            self.logger.debug(f"Data contains 'False': {data.data[1]}")
            self.collector.collect(data, 1)
        else:
            self.logger.debug(f"Data does not contain 'False': {data.data[1]}")
            self.collector.collect(data, 0)