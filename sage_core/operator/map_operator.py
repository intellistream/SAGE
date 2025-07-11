from .base_operator import BaseOperator

from typing import Union
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from sage_runtime.io.packet import Packet


class MapOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def receive_packet(self, packet: 'Packet' = None):
        """
        Smart dispatch for multi-input operator.
        """
        self.logger.debug(f"Received packet in operator {self.name}")
        try:
            if packet is None or packet.payload is None:
                result = self.function.execute()
                self.logger.debug(f"Operator {self.name} received empty packet, executed with result: {result}")
            else:
                result = self.function.execute(packet.payload)
                self.logger.debug(f"Operator {self.name} processed payload with result: {result}")
            if result is not None:
                self.emit(Packet(result))
        except Exception as e:
            self.logger.error(f"Error in {self.name}.receive_packet(): {e}", exc_info=True)