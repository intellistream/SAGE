from .base_operator import BaseOperator
from sage_core.api.tuple import Data
from typing import Union
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger



class MapOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)