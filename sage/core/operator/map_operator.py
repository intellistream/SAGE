from .base_operator import BaseOperator, Data
from typing import TypeVar,Generic, Callable, Any, List, Union
from sage.api.base_function import BaseFunction
from sage.core.io.emit_context import BaseEmitContext
from sage.utils.custom_logger import CustomLogger



class MapOperator(BaseOperator):
    def __init__(self,
                function:Union[BaseFunction,type[BaseFunction]],
                *args, **kwargs):
        super().__init__()
        session_folder = kwargs.pop("session_folder", None)
        self.function = function

        # 创建 Custom Logger
        self.logger = CustomLogger(
            object_name = f"Operator_{self.function.__class__.__name__}",
            session_folder = session_folder,
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )


    # def execute(self, *args, **kwargs):
    #     """
    #     Override this method with actual operator logic in subclasses.
    #     """
    #     raise NotImplementedError(f"{self._name}.execute() is not implemented")

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
    
    # 直接使用基类BaseOperator的emit方法
    # def emit(self, channel: int, data: Any):
    #     """
    #     Emit data to downstream node through specified channel.
    #     The actual emission is handled by the emit context.
        
    #     Args:
    #         channel: The output channel number
    #         data: The data to emit
    #     """
    #     if self._emit_context is None:
    #         raise RuntimeError(f"Emit context not set for operator {self._name}. "
    #                          "This should be injected by the DAG node.")
    #     self._emit_context.emit(channel, data)

