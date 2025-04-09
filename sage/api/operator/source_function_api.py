from sage.api.operator.base_operator_api import BaseOperator
from typing import Any
from abc import abstractmethod
class SourceFunction(BaseOperator):
    """
    Operator for read data
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self, context: Any = None) -> str:
        raise NotImplementedError("SourceFunction must implement execute() method")