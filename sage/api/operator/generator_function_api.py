from sage.api.operator.base_operator_api import StateLessFuction,Data,T
from abc import abstractmethod
class GeneratorFunction(StateLessFuction):
    """
    Operator for get LLM response
    """
    def __init__(self):
        super().__init__()
        # Default model can be set or passed by subclass
        self.model = None
    @abstractmethod
    def execute(self, data:Data[T]) -> Data[T]:
        """
        Subclasses must override this method to implement generation logic.
        """
        if self.model is None:
            raise ValueError("No model has been assigned to GeneratorFunction")
        
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
