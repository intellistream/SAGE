from sage.core.operator.base_operator import BaseOperator
from sage.core.api.function.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any, TYPE_CHECKING
from sage.core.communication.packet import Packet

class SourceOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def receive_packet(self, packet: 'Packet'):
        self.process_packet(packet)

    def process_packet(self, packet: 'Packet' = None):
        try:
            
            result = self.function.execute()
            self.logger.debug(f"Operator {self.name} processed data with result: {result}")
            if result is not None:
                self.logger.info(f"SourceOperator {self.name}: Sending packet with payload: {result}")
                success = self.router.send(Packet(result))
                self.logger.info(f"SourceOperator {self.name}: Send result: {success}")
                # If sending failed (e.g., queue is closed), stop the task
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
