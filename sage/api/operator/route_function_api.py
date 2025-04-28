from sage.api.operator.base_operator_api import BaseOperator,Data
from typing import Any, Tuple, List
from abc import abstractmethod

class RouterFunction(BaseOperator):
    """
    Operator for retrieve from memory
    """
    def __init__(self,):
        super().__init__()
        pass


    # Returns both the original query and the retrieved memory chunks
    @abstractmethod
    def execute(self):
        raise NotImplementedError("RouterFunction must implement execute().")