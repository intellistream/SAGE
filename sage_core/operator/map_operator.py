from .base_operator import BaseOperator
from sage_core.function.map_function import MapFunction

from typing import Union
from sage_core.function.map_function import MapFunction
from sage_utils.custom_logger import CustomLogger
from sage_runtime.io.packet import Packet


class MapOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # # 验证函数类型
        # if not isinstance(self.function, MapFunction):
        #     raise TypeError(f"{self.__class__.__name__} requires MapFunction, got {type(self.function)}")
        


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
                self.emit(result)
        except Exception as e:
            self.logger.error(f"Error in {self.name}.receive_packet(): {e}", exc_info=True)