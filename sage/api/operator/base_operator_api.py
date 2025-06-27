
import logging
from typing import TypeVar,Generic, Callable, Any, List

from typing import TypeVar,Generic
T = TypeVar('T')
class Data(Generic[T]):
    def __init__(self, data: T):
        self.data = data 





class BaseFuction:
    def __init__(self):
        self.upstream = None
        self.downstream = None
        self._name = self.__class__.__name__
        self.logger = logging.getLogger(self.__class__.__name__)

    def set_upstream(self, op):
        self.upstream = op
        if op:
            op.downstream = self

    def set_downstream(self, op):
        self.downstream = op
        if op:
            op.upstream = self

    def get_name(self):
        return self._name

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
                result = self.execute()
            else:
                result = self.execute(data)
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



    def set_emit_context(self, emit_context: 'EmitContext'):
        """
        Set the emit context that will be used when emit() is invoked.
        This is typically called by the DAG node during initialization.
        
        Args:
            emit_context: EmitContext instance that handles the emission
        """
        self._emit_context = emit_context
    
class StateLessFuction(BaseFuction):
    def __init__(self):
        super().__init__()
    
    def execute(self, data: Data[T]) -> Data[T]:
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")

class StatefulFuction(BaseFuction):
    def __init__(self):
        super().__init__()
        self._state = {}

    def execute(self, data: Data[T]) -> Data[T]:
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")

    def get_state(self):
        return self._state

class SharedStateFuction(BaseFuction):
    shared_state = {}  # class-level shared state

    def __init__(self):
        super().__init__()

    def execute(self, data: Data[T]) -> Data[T]:
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")

    @classmethod
    def get_shared_state(cls):
        return cls.shared_state

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
                result = self.execute()
            else:
                result = self.execute(data)
            if result is not None:
                self.emit(0, result)
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



    def set_emit_context(self, emit_context: 'EmitContext'):
        """
        Set the emit context that will be used when emit() is invoked.
        This is typically called by the DAG node during initialization.
        
        Args:
            emit_context: EmitContext instance that handles the emission
        """
        self._emit_context = emit_context

