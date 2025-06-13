from regex import D
from sage.api.operator.base_operator_api import StateLessFuction, Data,T
from abc import abstractmethod
class SinkFunction(StateLessFuction()):
    """
    Operator for output results
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self,data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement the sink logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
