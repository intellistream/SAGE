from sage.api.operator.base_operator_api import StateLessFuction,Data,T
from abc import abstractmethod
class ArxivFunction(StateLessFuction):
    """
    Operator for get Arxiv papers
    """
    def __init__(self):
        super().__init__()
        pass

    @abstractmethod
    def execute(self,data:Data[T]) -> Data[T]:
        """
        Subclasses must override this method.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")
