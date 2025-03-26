from sage.api.operator.base_operator_api import BaseOperator
from typing import Any

class SourceFunction(BaseOperator):
    def __init__(self):
        super().__init__()

    def execute(self, context: Any = None) -> str:
        raise NotImplementedError("SourceFunction must implement execute() method")