from .base_operator import BaseOperator, Data
from typing import Union
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger



class MapOperator(BaseOperator):
    def __init__(self,
                function:Union[BaseFunction,type[BaseFunction]],
                session_folder = None):
        super().__init__(function, session_folder)