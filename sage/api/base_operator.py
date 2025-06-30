
import logging
from typing import TypeVar,Generic, Callable, Any, List, Union
from sage.api.base_function import BaseFunction

T = TypeVar('T')
class Data(Generic[T]):
    def __init__(self, data: T):
        self.data = data 





class BaseOperator:
    def __init__(self, function:Union[BaseFunction,type[BaseFunction]] = None,*args, **kwargs):
        self._name = self.__class__.__name__
        self.logger = logging.getLogger(self.__class__.__name__)
        if(isinstance(function, BaseFunction)):
            self.function = function
        elif(isinstance(function, type) and issubclass(function, BaseFunction)):
            self.function = function(*args,**kwargs)


    def execute(self, *args, **kwargs):
        """
        Override this method with actual operator logic in subclasses.
        """
        raise NotImplementedError(f"{self._name}.execute() is not implemented")

    def receive(self, channel: int, data: Data):
        """
        Receive data from upstream node through specified channel.
        Default implementation calls execute() and emits result to channel 0.
        Can be overridden by subclasses for custom receive logic.
        
        Args:
            channel: The input channel number
            data: The data received from upstream
        """
        try:
            # Default behavior: call execute with received data and emit to channel 0
            if(data is None):
                result = self.function.execute()
            else:
                result = self.function.execute(data)
            if result is not None:
                self.emit(-1, result)
                # Note: Using -1 to indicate broadcasting to each output channel
        except Exception as e:
            self.logger.error(f"Error in {self._name}.receive(): {e}")
            raise

    def emit(self, channel: int, data: Any):
        """
        Emit data to downstream node through specified channel.
        The actual emission is handled by the emit context.
        
        Args:
            channel: The output channel number
            data: The data to emit
        """
        if self._emit_context is None:
            raise RuntimeError(f"Emit context not set for operator {self._name}. "
                             "This should be injected by the DAG node.")
        self._emit_context.emit(channel, data)



    def set_emit_context(self, emit_context):
        """
        Set the emit context that will be used when emit() is invoked.
        This is typically called by the DAG node during initialization.
        
        Args:
            emit_context: EmitContext instance that handles the emission
        """
        self._emit_context = emit_context
    
