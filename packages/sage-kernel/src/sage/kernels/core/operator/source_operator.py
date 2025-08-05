from sage.kernels.core.operator.base_operator import BaseOperator
from sage.api.function.source_function import SourceFunction
from sage.utils.logging.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any, TYPE_CHECKING
from sage.kernels.runtime.communication.router.packet import Packet
from sage.api.function.source_function import StopSignal
if TYPE_CHECKING:
    from sage.kernels.runtime.task.base_task import BaseTask

class SourceOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def receive_packet(self, packet: 'Packet'):
        self.process_packet(packet)

    def process_packet(self, packet: 'Packet' = None):
        try:
            
            result = self.function.execute()
            self.logger.debug(f"Operator {self.name} processed data with result: {result}")
            if isinstance(result, StopSignal):
                self.logger.info(f"Source Operator {self.name} received stop signal: {result}")
                result.name = self.name
                self.router.send_stop_signal(result)
                self.task.stop()
                return
            if result is not None:
                self.logger.info(f"SourceOperator {self.name}: Sending packet with payload: {result}")
                success = self.router.send(Packet(result))
                self.logger.info(f"SourceOperator {self.name}: Send result: {success}")
                # If sending failed (e.g., queue is closed), stop the task
                if not success:
                    self.logger.warning(f"Source Operator {self.name} failed to send packet, stopping task")
                    if hasattr(self, 'task') and hasattr(self.task, 'stop'):
                        self.task.stop()
                    return
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
