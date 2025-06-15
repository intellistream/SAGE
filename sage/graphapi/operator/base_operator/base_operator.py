from typing import Type, TYPE_CHECKING, Union, Any, Tuple
class BaseOperator:
    """
    Base class for all operators in the Sage Graph API.
    This class provides a common interface and basic functionality for all operators.
    """
    def __init__(self, name: str):
        pass

    def execute(self, data:Any, channel:int)->Tuple[Any, int]:
        """
        Execute the operator with the given arguments.
        This method should be overridden by subclasses to provide specific functionality.
        """
        raise NotImplementedError("Subclasses must implement the execute method.")