from abc import abstractmethod
from sage.api.operator.base_operator_api import StateLessFuction, Data, T
class RefinerFunction(StateLessFuction):
    """
    Operator for compress the prompt to speed up inference
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self,data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement the refiner logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")