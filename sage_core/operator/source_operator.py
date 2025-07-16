from sage_core.operator.base_operator import BaseOperator
from sage_core.function.source_function import SourceFunction
from sage_utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any
from sage_runtime.io.packet import Packet

class SourceOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        
    def process_packet(self, packet: 'Packet' = None):
        try:
            
            result = self.function.execute()
            self.logger.debug(f"Operator {self.name} processed data with result: {result}")
            if result is not None:
                self.emit_packet(Packet(result))
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
