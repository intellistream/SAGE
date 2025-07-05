from sage_core.api.tuple import Data
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from typing import Tuple, List, Union


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

    def execute(self, data: Data[Tuple[str, str]], channel:int):
        self.collector.collect(data, 0)
            