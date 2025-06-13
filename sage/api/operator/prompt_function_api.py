from sage.api.operator.base_operator_api import StateLessFuction, Data, T
from abc import abstractmethod

class PromptFunction(StateLessFuction()):
    """
    Operator for generating prompts based on input data.
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self, data: Data[T]) -> Data[T]:
        """
        Subclasses must override this method.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
