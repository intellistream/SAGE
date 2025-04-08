from sage.api.operator.base_operator_api import BaseOperator
from abc import abstractmethod

class WriterFunction(BaseOperator):
    """
    """
    def __init__(self):
        super().__init__()
        pass
    
    @abstractmethod
    def execute(self):
        raise NotImplementedError("WriterFunction must implement execute().")