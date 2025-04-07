from sage.api.operator.base_operator_api import BaseOperator
from typing import Any
from abc import abstractmethod
class SinkFunction(BaseOperator):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self):
        raise NotImplementedError("SinkFunction must implement execute() method")