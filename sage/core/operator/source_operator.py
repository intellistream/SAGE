from sage.core.operator.base_operator import BaseOperator
from sage.core.function.source_function import SourceFunction
from sage.utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any, TYPE_CHECKING
from sage.runtime.router.packet import Packet
from sage.core.function.source_function import StopSignal
if TYPE_CHECKING:
    from sage.runtime.task.base_task import BaseTask

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
                self.router.send(Packet(result))
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
