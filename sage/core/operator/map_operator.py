from .base_operator import BaseOperator
from sage.core.function.map_function import MapFunction

from typing import Union, Any
from sage.core.function.map_function import MapFunction
from sage.utils.custom_logger import CustomLogger
from sage.runtime.router.packet import Packet


class MapOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # # 验证函数类型
        # if not isinstance(self.function, MapFunction):
        #     raise TypeError(f"{self.__class__.__name__} requires MapFunction, got {type(self.function)}")
        
    def process_packet(self, packet: 'Packet' = None):
        try:
            if packet is None or packet.payload is None:
                self.logger.warning(f"Operator {self.name} received empty data")
            else:
                result = self.function.execute(packet.payload)
                self.logger.debug(f"Operator {self.name} processed data with result: {result}")
                result_packet = packet.inherit_partition_info(result) if (result is not None) else None
                if result_packet is not None:
                    self.router.send(result_packet)
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)