from sage.api.operator.base_operator_api import SharedStateFuction,StatefulFuction,Data,T
from abc import abstractmethod

class StateWriterFunction(StatefulFuction):
    """
    Operator for write private memory
    """
    def __init__(self):
        super().__init__()
        pass
    
    @abstractmethod
    def execute(self,data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement the writer logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
    
    
class SharedStateWriterFunction(SharedStateFuction):
    """
    Operator for write shared memory
    """
    def __init__(self):
        super().__init__()
        pass
    
    @abstractmethod
    def execute(self,data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement the writer logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented") 
