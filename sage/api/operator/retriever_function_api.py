from sage.api.operator.base_operator_api import StatefulFuction,SharedStateFuction,Data,T
from abc import abstractmethod

class StateRetrieverFunction(StatefulFuction):
    """
    Operator for retrieve from private memory
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self,data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement the retriever logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
class SharedStateRetrieverFunction(SharedStateFuction):
    """
    Operator for retrieve from shared memory
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self,data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement the retriever logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
    

