from sage.api.operator.base_operator_api import StateLessFuction,Data,T
from abc import abstractmethod
class EvaluateFunction(StateLessFuction):
    """
    Operator for evaluating data.
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self, data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement evaluation logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
