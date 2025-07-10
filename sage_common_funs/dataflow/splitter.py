from sage_core.api.tuple import Data
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from typing import Tuple, List, Union, Type, Any


class Splitter(BaseFunction):
    """
    Splitter function to split a tuple into multiple outputs.
    This is useful for splitting data into multiple streams.
    """

    def __init__(self, config: dict = None,  **kwargs):
        super().__init__(**kwargs)

    @classmethod # 多路输出的function可以override这个方法
    def declare_outputs(cls) -> List[Tuple[str, Type]]:
        return [("true", Any), ("false", Any)]
    
    def execute(self, data: Data[Tuple[str, str]]):
        if(data.data[1].find("False") != -1):
            self.logger.debug(f"Data contains 'False': {data.data[1]}")
            self.out.collect(data, "false")
        else:
            self.logger.debug(f"Data does not contain 'False': {data.data[1]}")
            self.out.collect(data, "true")