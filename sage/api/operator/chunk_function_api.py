from sage.api.operator.base_operator_api import StateLessFuction, Data, T
from abc import abstractmethod

class ChunkFunction(StateLessFuction):
    """
    Operator for chunking data into smaller pieces.
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self,data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement chunking logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
