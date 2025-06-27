from typing import Type, TYPE_CHECKING, Union, Any, Tuple, Callable
class BaseFunction:
    """
    Base class for all operators in the Sage Graph API.
    This class provides a common interface and basic functionality for all operators.
    """
    def __init__(self, name: str):
        self._emit_func: Callable[[int, Any], None] = None
        pass

    def receive(self,channel:int, data:Any ):
        """
        Execute the operator with the given arguments.
        This method should be overridden by subclasses to provide specific functionality.
        """
        raise NotImplementedError("Subclasses must implement the execute method.")
    
    def emit(self, channel:int, data:Any):
        if self._emit_func is None:
            raise RuntimeError("Emit function not set.")
        self._emit_func(channel, data)
        # 在dagnode中注入emit function
    def set_emit_func(self, emit_func: Callable[[int, Any], None]):
        self._emit_func = emit_func