from sage.api.operator.base_operator_api import StateLessFuction,Data,T
from abc import abstractmethod

class RouterFunction(StateLessFuction()):
    """
    Operator for routing data to different processing paths based on conditions.
    """
    def __init__(self,):
        super().__init__()

    @abstractmethod
    def execute(self):
        """
        Subclasses must override this method to implement the routing logic.
        """
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")